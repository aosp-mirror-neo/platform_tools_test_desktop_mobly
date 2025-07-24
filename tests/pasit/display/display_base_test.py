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

from lib.pasit import display_helper
from lib.pasit import display_painter
from lib.pasit import pasit_display
from lib.pasit import pasit_test
from lib.utils import image
from lib.utils import retry
from mobly import asserts
from mobly import signals


class DisplayBaseTest(pasit_test.PasitTestClass):
  """Base test for PASIT display tests."""

  display: pasit_display.PasitDisplay
  painter: display_painter.DisplayPainter
  helper: display_helper.DisplayHelper
  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_MONITOR

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

  def teardown_test(self):
    self.painter.clean_color_on_display()
    super().teardown_test()

  def teardown_class(self):
    """Handle the teardown for the class."""
    self.painter.cleanup()
    super().teardown_class()

  def _plug_in_external_display(self):
    """Emulate external display plug in using passport."""
    logging.info('Plugging in external display')
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_MONITOR)

  def _unplug_external_display(self):
    """Emulate external display unplug using passport."""
    logging.info('Unplugging external display')
    self.passport_host.deactivate_device_by_type(self.DEVICE_TYPE_MONITOR)

  def _verify_display_count(self, expected_count: int, event_to_log: str):
    """Verifies that the display count is equal to the expected count."""
    asserts.assert_equal(
        retry.retry(
            self.display.get_display_count,
            until=lambda count: count == expected_count,
            max_tries=10,
            delay_seconds=2,
        ),
        expected_count,
        f'Display count is not {expected_count} {event_to_log}.',
    )

  def _verify_captured_color(
      self,
      camera_id: str,
      expected_color: image.Color,
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
    match_color = self.helper.capture_color(
        camera_id, f'{camera_capture_name}_from_camera{camera_id}'
    )
    logging.info(
        'Camera %s detected color %s with display color %s',
        camera_id,
        match_color.name if match_color else 'None',
        expected_color,
    )
    asserts.assert_is_not_none(match_color, failure_message)
    asserts.assert_equal(
        match_color.value if match_color else None,
        expected_color,
        failure_message,
    )

  def _map_displays_to_cameras_with_retries(self) -> dict[str, str]:
    """Maps the displays to cameras with retry every 10 seconds."""
    # TODO: b/431215234 - Remove the retry once the bug is fixed.
    return retry.retry(
        self.helper.map_displays_to_cameras,
        max_tries=3,
        delay_seconds=10,
        exceptions=(signals.TestError,),
    )
