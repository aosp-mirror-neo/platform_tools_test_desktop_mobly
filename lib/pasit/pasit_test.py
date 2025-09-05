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

import types
from typing import Any

from chromiumos.test.lab.api import pasit_host_pb2
from lib.pasit import dut_state_manager
from lib.pasit import pasit_device
from lib.pasit.passport import passport_host
from mobly import asserts
from mobly import base_test
from mobly import records
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

  dut: pasit_device.PasitDevice
  requires_device_type: pasit_host_pb2.PasitHost.Device.Type = None

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
    self.dut = pasit_device.create(self)
    self.passport_host.reset()

  def teardown_test(self):
    """Teardown steps after each test is executed."""
    # ensure that the passport switches are disabled after the test
    self.passport_host.reset()
    if self.dut.power_on_if_offline():
      asserts.fail('DUT is offline after test.')
    super().teardown_test()

  def teardown_class(self):
    """Teardown steps after all tests are executed."""
    if hasattr(self, 'dut'):
      self.dut.cleanup()
    super().teardown_class()

  def on_fail(self, record: records.TestResultRecord):
    """Called on test failure."""
    if hasattr(self, 'pasport_host'):
      self.passport_host.capture_images_from_all_cameras(
          self.current_test_info.output_path, 'on_fail'
      )
    self._capture_screenshots('on_fail_screenshot')
    super().on_fail(record)

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

  def _create_passport_controller(self) -> passport_host.PassportHost:
    """Create passport host controller from the testbed configuration."""
    if 'PassportHost' in self.controller_configs:
      return self.register_controller(passport_host)[0]
    else:
      raise signals.TestError(
          'No PassportHost found for controller config:'
          f' {self.controller_configs}'
      )

  def _skip_if_servo_needed_and_not_configured(
      self, desired_state: dut_state_manager.PowerState
  ):
    """Skip the test if servo is required and not configured."""
    asserts.skip_if(
        dut_state_manager.requires_servo(desired_state)
        and not self.dut.is_servo_configured(),
        'Test requires servo and servo is not configured.',
    )

  def _capture_screenshots(self, name_prefix: str):
    """Capture screenshots and save them to the test output directory."""
    if hasattr(self, 'dut'):
      self.dut.capture_screenshots(
          self.current_test_info.output_path, name_prefix
      )
