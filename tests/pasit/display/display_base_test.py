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

"""Base test for PASIT display tests."""

import logging

from lib.pasit import display_camera_mapper
from lib.pasit import display_helper
from lib.pasit import display_painter
from lib.pasit import pasit_display
from lib.pasit import pasit_test
from lib.pasit import peripheral_connector
from lib.pasit import test_policy
from lib.utils import image
from lib.utils import retry
from mobly import asserts


class DisplayBaseTest(pasit_test.PasitTestClass):
  """Base test for PASIT display tests."""

  display: pasit_display.PasitDisplay
  painter: display_painter.DisplayPainter
  helper: display_helper.DisplayHelper
  camera_mapper: display_camera_mapper.DisplayCameraMapper
  peripheral_connector: peripheral_connector.PeripheralConnector
  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_MONITOR
  reboot_policy = test_policy.DisplayTestPolicy.REBOOT_POLICY

  def setup_class(self):
    """Handle the setup for the test.

    Create PasitDisplay for the interacting with displays.
    """
    super().setup_class()
    self.display = self.create(pasit_display)
    self.painter = self.create(display_painter)
    self.peripheral_connector = peripheral_connector.PeripheralConnector(
        self.passport_host
    )

  def setup_test(self):
    """Handle the setup for the test."""
    super().setup_test()
    self.helper = display_helper.DisplayHelper(self.display)
    self.camera_mapper = display_camera_mapper.DisplayCameraMapper(
        self.passport_host,
        self.display,
        self.painter,
        self.current_test_info.output_path,
    )

  def teardown_test(self):
    """Handle the teardown for the test."""
    self.display.save_debug_info(self.current_test_info.output_path)
    self.painter.safe_clean_color_on_display()
    super().teardown_test()

  def teardown_class(self):
    """Handle the teardown for the class."""
    if hasattr(self, 'painter'):
      self.painter.cleanup()
    super().teardown_class()

  def _get_display_path_tag(
      self,
      connection_type: peripheral_connector.ConnectionType,
      min_display_count: int = 1,
  ) -> peripheral_connector.ConnectionTag | None:
    """Get the connection tag to use for the display path.

    This will determine the tag to use when enabling/disabling the display. And
    will skip the test if the display path cannot be determined.

    Args:
      connection_type: The type of connection to use for the display.
      min_display_count: The minimum number of displays required for the test.

    Returns:
      The connection tag to use for the display.
    """
    try:
      return self.peripheral_connector.get_peripheral_path_tag(
          self.DEVICE_TYPE_MONITOR, connection_type, min_display_count
      )
    except (
        peripheral_connector.PeripheralNotFoundError,
        peripheral_connector.PeripheralPathNotFoundError,
    ) as e:
      asserts.skip(f'No display path found: {e}')
    except peripheral_connector.PeripheralCountMismatchError as e:
      asserts.skip(
          f'Display count {e.peripheral_count} is less than minimum required'
          f' count of {e.min_peripheral_count} displays for this test.'
      )

  def plug_in_external_displays(
      self,
      external_display_count: int,
      connection_type: peripheral_connector.ConnectionType = peripheral_connector.ConnectionType.ANY,
  ):
    """Emulate multiple external display plug in using passport.

    Skips the test if the number of monitors in the topology is less than the
    given display count.

    Args:
      external_display_count: The number of external displays to plug in.
      connection_type: The type of connection to use for the displays.
    """
    display_path_tag = self._get_display_path_tag(
        connection_type, external_display_count
    )
    monitor_ids = self.peripheral_connector.get_peripheral_ids(
        self.DEVICE_TYPE_MONITOR, display_path_tag
    )

    for monitor_id in monitor_ids[:external_display_count]:
      logging.info('Plugging in external display %s', monitor_id)
      self.passport_host.activate_device_by_id(monitor_id, display_path_tag)

  def plug_in_external_display(
      self,
      connection_type: peripheral_connector.ConnectionType = peripheral_connector.ConnectionType.ANY,
  ):
    """Emulate external display plug in using passport."""
    display_path_tag = self._get_display_path_tag(connection_type)

    logging.info('Plugging in external display')
    self.passport_host.activate_device_by_type(
        self.DEVICE_TYPE_MONITOR, display_path_tag
    )

  def unplug_external_display(
      self,
      connection_type: peripheral_connector.ConnectionType = peripheral_connector.ConnectionType.ANY,
  ):
    """Emulate external display unplug using passport."""
    display_path_tag = self._get_display_path_tag(connection_type)

    logging.info('Unplugging external display')
    self.passport_host.deactivate_device_by_type(
        self.DEVICE_TYPE_MONITOR, display_path_tag
    )

  def verify_display_count(self, expected_count: int, event_to_log: str):
    """Verifies that the display count is equal to the expected count."""
    asserts.assert_equal(
        self.helper.get_display_count(expected_count),
        expected_count,
        f'Display IDs count is not {expected_count} {event_to_log}.',
    )

  def verify_captured_color(
      self,
      camera_id: str,
      expected_color: image.NamedColor,
      camera_capture_name: str,
      failure_message: str,
  ):
    """Verifies that the camera captured the expected color.

    Fails the test if the verification fails.

    Args:
      camera_id: The camera ID to use for the verification.
      expected_color: The expected color to verify.
      camera_capture_name: Prefix for the image name to use for the capture.
      failure_message: The message to use for the assertion if the verification
        fails.
    """
    match_status = retry.retry(
        lambda: self.camera_mapper.try_match_color(
            camera_id,
            expected_color,
            f'{camera_capture_name}_from_camera{camera_id}',
        ),
        until=lambda status: status,
        policy=test_policy.DisplayTestPolicy.MATCH_COLOR_RETRY_POLICY,
    )
    asserts.assert_true(
        match_status,
        failure_message,
    )
    logging.info(
        'Camera %s detected color %s as expected',
        camera_id,
        expected_color.name,
    )

  def map_displays_to_cameras_with_retries(
      self,
  ) -> dict[pasit_display.PasitDisplay.DisplayId, str]:
    """Maps the displays to cameras with retry every 10 seconds."""
    # TODO: b/431215234 - Remove the retry once the bug is fixed.
    return retry.retry(
        self.camera_mapper.map_displays_to_cameras,
        policy=test_policy.DisplayTestPolicy.MAP_DISPLAYS_TO_CAMERAS_RETRY_POLICY,
        exceptions=(display_camera_mapper.MapDisplaysToCamerasError,),
    )
