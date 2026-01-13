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

"""Base class for UCD tests that sets and resets the displays state between tests."""

import logging
import os
import time

from display.utils import modetest_helper
from display.utils import ucd_manager
from lib.pasit import display_helper
from lib.pasit import pasit_display
from lib.pasit import pasit_test
from lib.pasit import pasit_test_config
from lib.utils import image
from lib.utils import retry
from mobly import asserts


class UcdTestBase(pasit_test.PasitTestClass):
  """Base class for UCD tests.

  This class sets up and resets the displays state between tests.
  It also provides helper methods for checking the displays state.
  """

  class ColorMatchingError(Exception):
    """Error matching the screenshot of a display with the expected color.

    Raised when the screenshot of a display does not match the expected color or
    is black.
    """

  _ucd_manager: ucd_manager.UcdManager
  # Maximum number of displays that can be tested with the current DUT.
  max_tested_displays: int
  display: pasit_display.PasitDisplay
  helper: display_helper.DisplayHelper
  reboot_policy = pasit_test_config.RebootPolicy.ON_TEARDOWN_TEST

  disable_screen_recording = True

  _UCD_ABSOLUTE_MAX_CONNECTED_DISPLAYS = 4  # UCD-500 Ultimate max displays.
  _CROP_RATIO_FOR_COLOR_CHECK = 0.5

  def setup_class(self, require_servo: bool = False):
    super().setup_class()
    # Servo is required for DUT power cycle through servo.
    asserts.skip_if(
        require_servo and not self.dut.is_servo_configured(),
        "Servo is not configured.",
    )
    # Set the UCD.
    self._ucd_manager = ucd_manager.UcdManager.connect_to_ucd(
        self.passport_host.video_tester_client,
        self.dut,
    )
    self._ucd_manager.unplug_all_displays(wait_for_active=True)
    # Set the max number of displays that can be tested.
    max_crtc_on_dut = modetest_helper.get_crtcs_count(self.dut)
    theoritical_max_connected_displays = max_crtc_on_dut - 1  # 1 is used by eDP
    self.max_tested_displays = min(
        self._ucd_manager.max_supported_displays,
        theoritical_max_connected_displays,
    )
    logging.info("max_tested_displays: %d", self.max_tested_displays)
    asserts.assert_greater(
        self.max_tested_displays,
        0,
        "No displays are supported by the system: max_crtc_on_dut:"
        f" {max_crtc_on_dut}, max_supported_displays:"
        f" {self._ucd_manager.max_supported_displays}",
    )
    self.display = self.create(pasit_display)
    self.helper = display_helper.DisplayHelper(self.display)
    self.internal_display_id = self.helper.get_internal_display_id()

  def teardown_test(self):
    try:
      self._ucd_manager.unplug_all_displays(wait_for_active=False)
    except Exception:  # pylint: disable=broad-except
      pass

    super().teardown_test()

  def teardown_class(self):
    self._ucd_manager.reset_ucd_displays_state_to_default()
    self._ucd_manager.disconnect_ucd()
    super().teardown_class()

  def skip_if_display_count_not_supported(self, display_count: int):
    """Skips the test if the display count to test is greater than the maximum supported displays."""
    asserts.skip_if(
        display_count > self.max_tested_displays,
        f"{display_count} is greater than the maximum supported"
        f" {self.max_tested_displays}.",
    )

  def check_all_screenshots_for_displays(
      self, display_count: int, color: image.Color | None = None
  ):
    """Checks if the screenshots of the specified displays are valid.

    This function iterates through the specified number of displays, takes a
    screenshot of each, and verifies its content. If a `color` is provided,
    it checks if the screenshot matches that color; otherwise, it checks if it's
    not black.
    Retries as the display might not be ready yet when checked.

    Args:
        display_count: The number of displays to check.
        color: Optional RGB color to check against the screenshot. If provided,
          the function will verify that the screenshot matches this color. If
          None, it will only check that the screenshot is not black.

    Raises:
        ColorMatchingError: If any screenshot does not match the expected color
        or is black.

    Returns:
        True if all screenshots are valid (not black or match the expected
        color).
    """
    for i in range(display_count):
      retry.retry(
          lambda i=i: self._check_single_display_screenshot(i, color),
          policy=retry.RetryPolicy(max_tries=3, delay_seconds=3),
          exceptions=(self.ColorMatchingError,),
      )

  def _check_single_display_screenshot(
      self, display_index: int, color: image.Color | None
  ):
    """Checks the screenshot for a single display, raising an exception on failure.

    Args:
        display_index: The index of the display to check.
        color: Optional RGB color to check against the screenshot. If provided,
          the function verifies that the screenshot matches this color. If None,
          it will only check that the screenshot is not black.

    Returns:
        True if the screenshot is valid (not black or matches the expected
        color).

    Raises:
        ColorMatchingError: If the screenshot does not match the expected color
        or is black.
    """
    logging.debug("Checking screenshot for display %d", display_index)
    screenshot_bmp = self._ucd_manager.get_display_screenshot(display_index)
    screenshot_raw, width, height = image.process_bmp_img_to_raw(screenshot_bmp)

    timestamp = int(time.time())

    if color:
      filename = f"display_{display_index}_{color}_{timestamp}_raw.bmp"
      if not image.check_rgb_image_matches_color(
          screenshot_raw,
          color,
          width,
          height,
          crop_ratio=self._CROP_RATIO_FOR_COLOR_CHECK,
      ):
        self._save_screenshot(screenshot_bmp, filename)
        raise self.ColorMatchingError(
            "Screenshot for display"
            f" {display_index} does not match the expected color {color}. Saved"
            f" to {filename}."
        )
      logging.info(
          "Screenshot for display %d matches the expected color %s.",
          display_index,
          color,
      )

    else:
      filename = f"display_{display_index}_{timestamp}_raw.bmp"
      if not image.is_rgb_image_not_black(screenshot_raw):
        self._save_screenshot(screenshot_bmp, filename)
        raise self.ColorMatchingError(
            f"Screenshot for display {display_index} is black. Saved to"
            f" {filename}."
        )
      logging.info("Screenshot for display %d is not black.", display_index)

  def _save_screenshot(self, data: bytes, filename: str):
    """Saves binary data to a file in the test's log directory.

    Args:
        data: The binary data to save
        filename: The name of the file to create
    """
    filepath = os.path.join(self.log_path, filename)
    logging.info("Saving screenshot to %s", filepath)

    with open(filepath, "wb") as f:
      f.write(data)
