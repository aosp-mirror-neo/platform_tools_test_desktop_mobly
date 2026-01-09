# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Base test class for PASIT Mobly tests."""

import logging
import time
import types
from typing import Any

from chromiumos.test.lab.api import pasit_host_pb2
from lib.pasit import dut_state_manager
from lib.pasit import pasit_device
from lib.pasit.passport import passport_host as passport_host_module
from mobly import asserts
from mobly import base_test
from mobly import signals


def get_device_type_name(
    device_type: pasit_host_pb2.PasitHost.Device.Type,
) -> str:
  return (
      pasit_host_pb2.PasitHost.Device.Type.Name(device_type)
      if device_type
      else ''
  )


class PasitTestClass(base_test.BaseTestClass):
  """Base test class for PASIT Mobly tests."""

  DEVICE_TYPE_STORAGE = pasit_host_pb2.PasitHost.Device.Type.STORAGE
  DEVICE_TYPE_CAMERA = pasit_host_pb2.PasitHost.Device.Type.CAMERA
  DEVICE_TYPE_MONITOR = pasit_host_pb2.PasitHost.Device.Type.MONITOR
  DEVICE_TYPE_HID = pasit_host_pb2.PasitHost.Device.Type.HID
  DEVICE_TYPE_DOCK = pasit_host_pb2.PasitHost.Device.Type.DOCKING_STATION
  DEVICE_TYPE_NETWORK = pasit_host_pb2.PasitHost.Device.Type.NETWORK

  dut: pasit_device.PasitDevice
  requires_device_type: pasit_host_pb2.PasitHost.Device.Type = None
  disable_screen_recording: bool = False
  bugreport: str
  failure_pause_seconds: int
  failure_drop_to_interpreter: bool
  passport_host: passport_host_module.PassportHost

  def setup_class(self):
    """Setup steps before any test is executed."""
    super().setup_class()
    self.passport_host = self._create_passport_controller()
    asserts.abort_class_if(
        self.requires_device_type
        and not self.passport_host.is_device_type_present(
            self.requires_device_type, None
        ),
        'Device type '
        f'{get_device_type_name(self.requires_device_type)}'
        ' not found in topology.',
    )
    self.bugreport = self.user_params.get('bugreport', 'on_fail')
    self.failure_pause_seconds = int(
        self.user_params.get('on_fail_pause_seconds', '0')
    )
    self.failure_drop_to_interpreter = bool(
        self.user_params.get('on_fail_drop_to_interpreter', False)
    )
    self._apply_retry_and_repeat_to_all_tests()

    self.dut = pasit_device.create(self)
    self.passport_host.reset()

    self.passport_host.save_topology_diagram(self.log_path)

  def setup_test(self):
    """Setup steps before each test is executed."""
    super().setup_test()
    if not self.disable_screen_recording:
      self.dut.start_screen_recording()

  def teardown_test(self):
    """Teardown steps after each test is executed."""
    # 1) stop the screen recording before cold reset in power_on_if_offline()
    self._stop_screen_recording()

    # 2) power on the DUT if it is offline after the test
    dut_offline_after_test = False
    try:
      dut_offline_after_test = self.dut.power_on_if_offline()
    except pasit_device.PasitDeviceError as e:
      logging.warning('Failed to power on DUT: %s', e)
      asserts.abort_class(
          'The DUT is unexpectedly offline and recovery failed.'
      )

    # 3) if the DUT is online, copy the screen recording files to the test
    #    output path.
    self._stop_screen_recording(self.current_test_info.output_path)

    # 4) fail the test if the DUT is offline or unexpectedly rebooted.
    if dut_offline_after_test:
      asserts.fail('DUT is offline after test.')
    elif self.dut.unexpected_reboots():
      asserts.fail('DUT unexpectedly rebooted during test.')

    # ensure that the passport switches are disabled after the test
    self.passport_host.reset()
    super().teardown_test()

  def teardown_class(self):
    """Teardown steps after all tests are executed."""
    if hasattr(self, 'dut'):
      # stop the screen recording here in case teardown_test was not executed
      self._stop_screen_recording(self.root_output_path)
      self.dut.cleanup()
    super().teardown_class()

  def _stop_screen_recording(self, output_path: str | None = None) -> None:
    """Stops the screen recording and copies the files to the output path."""
    if not self.disable_screen_recording:
      self.dut.stop_screen_recording(output_path)

  def create(self, module: types.ModuleType) -> Any:
    """Create a component utility instance for the test Mobly controller.

    Args:
      module: The module must have a field named `registry` which is a
        dictionary of controller type as the key, and corresponding component
        utility class as the value.

    Returns:
      A component utility instance for particular Mobly controller.
    """
    controller = self.dut.controller
    for controller_type, func in module.registry.items():
      if controller_type == type(controller):
        return func(controller)
    raise signals.TestError(
        f'Unknown controller type: {type(controller).__name__}'
    )

  def _create_passport_controller(self) -> passport_host_module.PassportHost:
    """Create passport host controller from the testbed configuration."""
    if 'PassportHost' in self.controller_configs:
      return self.register_controller(passport_host_module)[0]
    else:
      raise signals.TestError(
          'No PassportHost found for controller config:'
          f' {self.controller_configs}'
      )

  def skip_if_servo_needed_and_not_configured(
      self, desired_state: dut_state_manager.PowerState
  ):
    """Skip the test if servo is required and not configured."""
    asserts.skip_if(
        dut_state_manager.requires_servo(desired_state)
        and not self.dut.is_servo_configured(),
        'Test requires servo and servo is not configured.',
    )

  def capture_screenshots(self, name_prefix: str):
    """Capture screenshots and save them to the test output directory."""
    if hasattr(self, 'dut'):
      self.dut.capture_screenshots(
          self.current_test_info.output_path, name_prefix
      )

  def _capture_bugreport(self, test_failed: bool) -> None:
    """Captures a bug report if configured to."""
    collect_bugreport = self.bugreport == 'all' or (
        self.bugreport == 'on_fail' and test_failed
    )
    if not collect_bugreport:
      return
    logging.info('Collecting bug report for test.')
    if self.dut.is_device_offline():
      logging.warning('DUT is offline, cannot collect bug report.')
      return
    try:
      self.dut.controller.take_bug_report(
          test_name=self.current_test_info.name,
          begin_time=self.current_test_info.record.begin_time,
          destination=self.current_test_info.output_path,
      )
    except Exception as e:  # pylint: disable=broad-except
      logging.warning('Failed to collect bug report: %s', e)

  def _debug_on_test_failure(self, e: Exception) -> None:
    """Pauses the test for debugging on test failure."""
    if self.failure_drop_to_interpreter:
      # must be assigned to a local variable to be accessible from the debugger
      test_instance = self
      logging.error('Dropping to interpreter due to test failure: %s.', e)
      logging.info(
          'You can access the test class from the debugger by using the'
          ' test_instance variable: %s',
          test_instance,
      )
      breakpoint()
    elif self.failure_pause_seconds > 0:
      logging.error(
          'Pausing for %d seconds after test failure: %s.',
          self.failure_pause_seconds,
          e,
      )
      time.sleep(self.failure_pause_seconds)

  def _try_create_excerpts(self) -> None:
    """Creates excerpts for all Mobly Services."""
    try:
      self.dut.controller.services.create_output_excerpts_all(
          self.current_test_info
      )
    except Exception as e:  # pylint: disable=broad-except
      logging.warning('Failed to create excerpts: %s', e)

  def _try_capture_screenshots(self) -> None:
    """Captures screenshots for all displays."""
    if self.dut.is_device_offline():
      logging.warning('DUT is offline, cannot capture screenshots.')
      return
    try:
      self.dut.capture_screenshots(
          self.current_test_info.output_path, 'on_test_failure'
      )
    except Exception as e:  # pylint: disable=broad-except
      logging.warning('Failed to capture screenshots: %s', e)

  def _try_capture_images_from_all_cameras(self) -> None:
    """Captures images from all cameras."""
    try:
      self.passport_host.capture_images_from_all_cameras(
          self.current_test_info.output_path, 'on_test_failure'
      )
    except Exception as e:  # pylint: disable=broad-except
      logging.warning('Failed to capture images from all cameras: %s', e)

  def _apply_retry_and_repeat_to_all_tests(self):
    """Applies retry and repeat decorators to all tests if retry_count is set.

    This allows for mimicking the repeat and retry decorators for all tests
    without having to explicitly decorate each test with the retry and repeat
    decorators.  Mostly useful for testing and recreating failures/flakes in
    the lab.
    """
    retry_count = int(self.user_params.get('retry_count', 0))
    repeat_count = int(self.user_params.get('repeat_count', 0))
    max_consecutive_error = int(
        self.user_params.get('max_consecutive_error', 0)
    )
    if not retry_count and not repeat_count:
      return
    if retry_count and retry_count <= 1:
      raise signals.TestError(
          f'The retry_count must be larger than 1, got {retry_count}.'
      )
    if repeat_count and repeat_count <= 1:
      raise signals.TestError(
          f'The `repeat_count` must be larger than 1, got "{repeat_count}".'
      )
    if max_consecutive_error and not repeat_count:
      raise signals.TestError(
          '`max_consecutive_error` can only be set when `repeat_count` is set'
      )

    for test_name in self.get_existing_test_names():
      if test_name in self._generated_test_table:
        test_method = self._generated_test_table[test_name]
      else:
        test_method = getattr(type(self), test_name)

      # Do not override if already set by a decorator on a specific test.
      if not hasattr(test_method, base_test.ATTR_MAX_RETRY_CNT) and retry_count:
        setattr(test_method, base_test.ATTR_MAX_RETRY_CNT, retry_count)
      if not hasattr(test_method, base_test.ATTR_REPEAT_CNT) and repeat_count:
        setattr(test_method, base_test.ATTR_REPEAT_CNT, repeat_count)
      if (
          not hasattr(test_method, base_test.ATTR_MAX_CONSEC_ERROR)
          and max_consecutive_error
      ):
        setattr(
            test_method,
            base_test.ATTR_MAX_CONSEC_ERROR,
            max_consecutive_error,
        )

  # Note type hints intentionally not included to match underlying Mobly code
  # in base_test.py.
  def exec_one_test(self, test_name, test_method, record=None):
    """Override the Mobly exec_one_test method to allow for debugging."""

    def wrapped_test_method():
      try:
        test_method()
        # stop the screen recording before capturing the bugreport because
        # bugreport may take a DUT offline
        self._stop_screen_recording()
        self._capture_bugreport(False)
      # pylint: disable-next=try-except-raise
      except (signals.TestPass, signals.TestAbortSignal, signals.TestSkip):
        raise
      except Exception as e:
        # stop the screen recording before capturing the bugreport because
        # bugreport may take a DUT offline
        self._stop_screen_recording()
        self._capture_bugreport(True)
        self._try_capture_screenshots()
        self._try_capture_images_from_all_cameras()
        self._try_create_excerpts()
        self._debug_on_test_failure(e)
        raise e

    return super().exec_one_test(test_name, wrapped_test_method, record)
