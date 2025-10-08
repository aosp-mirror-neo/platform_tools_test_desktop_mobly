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

import enum
import logging

from lib.pasit import display_helper
from lib.pasit import display_painter
from lib.pasit import pasit_display
from lib.pasit import pasit_test
from lib.pasit import test_policy
from lib.utils import image
from lib.utils import retry
from mobly import asserts


class DisplayPaths(enum.StrEnum):
  DOCK = 'DOCK'
  DOCKLESS = 'DOCKLESS'
  DAISY_CHAIN = 'DAISY_CHAIN'


class DisplayBaseTest(pasit_test.PasitTestClass):
  """Base test for PASIT display tests."""

  display: pasit_display.PasitDisplay
  painter: display_painter.DisplayPainter
  helper: display_helper.DisplayHelper
  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_MONITOR

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.display_path_tag = None

  def setup_class(self):
    """Handle the setup for the test.

    Create PasitDisplay for the interacting with displays.
    """
    super().setup_class()
    self.display = self.create(pasit_display)
    self.painter = self.create(display_painter)

  def setup_test(self):
    """Handle the setup for the test."""
    super().setup_test()
    self.helper = display_helper.DisplayHelper(
        self.passport_host,
        self.display,
        self.painter,
        self.current_test_info.output_path,
    )
    self.display_path_tag = None

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

  def _determine_display_path(
      self, display_path: DisplayPaths
  ) -> DisplayPaths | None:
    """Determine the display path to use for the test.

    This will account for both tagged and untagged displays.  It defaults by
    searching for a display with a tag, and if none are found, it will attempt
    infer the path type of an untagged display.

    Returns:
      The display path to use for the test.
    Raises:
      ValueError: If the display path cannot be determined.
    """
    if not self.passport_host.is_device_type_present(
        self.DEVICE_TYPE_MONITOR, None
    ):
      raise ValueError('No displays found in topology.')
    if self.passport_host.is_device_type_present(
        self.DEVICE_TYPE_MONITOR, display_path
    ):
      return display_path
    paths = self.passport_host.get_paths_by_type(self.DEVICE_TYPE_MONITOR, None)
    # if there are no tagged paths attempt to infer the path type, by checking
    # whether or not a display is connected via a dock.  We only attempt to
    # infer if all the display paths are the same (dock or dockless).
    dock_path_count = 0
    for path in paths:
      for node in path:
        if (
            self.passport_host.get_device_by_id(node).type
            == self.DEVICE_TYPE_DOCK
        ):
          dock_path_count += 1

    if display_path == DisplayPaths.DOCK and dock_path_count == len(paths):
      return None
    if display_path == DisplayPaths.DOCKLESS and dock_path_count == 0:
      return None

    raise ValueError(f'Display path {display_path} not found in topology.')

  def setup_display_path(self, display_path: DisplayPaths):
    """Setup the display path for the test.

    This will determine the tag to use when enabling/disabling the display. And
    will skip the test if the display path cannot be determined.
    """
    try:
      self.display_path_tag = self._determine_display_path(display_path)
    except ValueError as e:
      asserts.skip(f'No display path found: {e}')

  def get_monitor_device_ids(self) -> list[str]:
    """Returns the device IDs of the monitors in the topology."""
    return self.passport_host.get_device_ids_by_type(self.DEVICE_TYPE_MONITOR)

  def plug_in_external_display(self, device_id: str | None = None):
    """Emulate external display plug in using passport."""
    if device_id:
      logging.info('Plugging in external display %s', device_id)
      self.passport_host.activate_device_by_id(device_id, self.display_path_tag)
    else:
      logging.info('Plugging in external display')
      self.passport_host.activate_device_by_type(
          self.DEVICE_TYPE_MONITOR, self.display_path_tag
      )

  def unplug_external_display(self, device_id: str | None = None):
    """Emulate external display unplug using passport."""
    if device_id:
      logging.info('Unplugging external display %s', device_id)
      self.passport_host.deactivate_device_by_id(
          device_id, self.display_path_tag
      )
    else:
      logging.info('Unplugging external display')
      self.passport_host.deactivate_device_by_type(
          self.DEVICE_TYPE_MONITOR, self.display_path_tag
      )

  def verify_display_count(self, expected_count: int, event_to_log: str):
    """Verifies that the display count is equal to the expected count."""
    asserts.assert_equal(
        retry.retry(
            lambda: len(self.display.get_display_ids()),
            until=lambda ids_count: ids_count == expected_count,
            policy=test_policy.DisplayTestPolicy.EXPECTED_DISPLAY_COUNT_RETRY_POLICY,
        ),
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
        lambda: self.helper.try_match_color(
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
        self.helper.map_displays_to_cameras,
        policy=test_policy.DisplayTestPolicy.MAP_DISPLAYS_TO_CAMERAS_RETRY_POLICY,
        exceptions=(display_helper.MapDisplaysToCamerasError,),
    )
