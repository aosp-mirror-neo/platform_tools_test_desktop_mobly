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
from lib.pasit import pasit_test
from lib.pasit.passport import errors
from lib.utils import image
from lib.utils.retry import retry
from mobly import asserts


PassportBaseError = errors.PassportBaseError


class UcdBaseTest(pasit_test.PasitTestClass):
  """Base class for UCD tests.

  This class sets up and resets the displays state between tests.
  It also provides helper methods for checking the displays state.
  """
  _ucd_manager: ucd_manager.UcdManager
  # Maximum number of displays that can be tested with the current DUT.
  max_tested_displays: int

  _UCD_ABSOLUTE_MAX_CONNECTED_DISPLAYS = 4

  def setup_class(self, require_servo: bool = False):
    super().setup_class()
    # Servo is required for DUT power cycle through servo.
    asserts.skip_if(
        require_servo and not self.dut.is_servo_configured(),
        "Servo is not configured.")
    # Set the UCD.
    self._ucd_manager = ucd_manager.UcdManager.connect_to_ucd(
        self.passport_host.video_tester_client,
        self.dut,
    )
    self._ucd_manager.unplug_and_destroy_all_displays()
    # Set the max number of displays that can be tested.
    max_crtc_on_dut = modetest_helper.get_crtcs_count(self.dut)
    theoritical_max_connected_displays = max_crtc_on_dut - 1  # 1 is used by eDP
    self.max_tested_displays = min(
        self._ucd_manager.max_supported_displays, theoritical_max_connected_displays
    )
    logging.info(f"max_tested_displays: {self.max_tested_displays}")
    asserts.assert_greater(
        self.max_tested_displays,
        0,
        "No displays are supported by the system: max_crtc_on_dut:"
        f" {max_crtc_on_dut}, max_supported_displays:"
        f" {self._ucd_manager.max_supported_displays}",
    )

  def teardown_test(self):
    try:
      # When we finish the test, ;et's check that the most basic functionalities are working.
      # If they're not, let's reset our system so we can start fresh after.
      self._perform_sanity_check()
      logging.debug("Sanity check passed.")
    except PassportBaseError:
      logging.info("Sanity check failed.")
      # If we fail, either the DUT or the UCD are having trouble.
      # Let's reconnect the UCD and reboot the DUT.
      self._ucd_manager.disconnect_ucd()
      self.dut.reboot()
      self._ucd_manager = ucd_manager.UcdManager.connect_to_ucd(
          self.passport_host.video_tester_client
      )
      # After a reboot, unplug everything (unplugging might have failed earlier).
      self._ucd_manager.unplug_and_destroy_all_displays()

  def teardown_class(self):
    self._ucd_manager.reset_ucd_displays_state_to_default()
    self._ucd_manager.disconnect_ucd()
    self.dut.reboot()

  def skip_if_display_count_not_supported(self, display_count: int):
    """Skips the test if the display count to test is greater than the maximum supported displays."""
    asserts.skip_if(
        display_count > self.max_tested_displays,
        f"{display_count} is greater than the maximum supported"
        f" {self.max_tested_displays}.",
    )

  def check_all_screenshots_for_displays(self, display_count: int, color: image.Color | None = None):
    """Checks if the screenshots of the specified displays are valid.

    This function iterates through the specified number of displays, takes a
    screenshot of each, and verifies its content. If a `color` is provided,
    it checks if the screenshot matches that color; otherwise, it checks if it's not black.
    Retries as the display might not be ready yet when checked.

    Args:
        display_count: The number of displays to check.
        color: Optional RGB color to check against the screenshot. If provided,
               the function will verify that the screenshot matches this color.
               If None, it will only check that the screenshot is not black.
    Raises:
        ValueError: If any screenshot does not match the expected
        color or is black.

    Returns:
        True if all screenshots are valid (not black or match the expected color).
    """
    for i in range(display_count):
      retry(
          func=lambda: self._check_single_display_screenshot(i, color),
          max_tries=3,
          delay_seconds=3,
          exceptions=(ValueError,),
      )

  def _check_single_display_screenshot(
      self, display_index: int, color: image.Color | None
  ):
    """Checks the screenshot for a single display, raising an exception on failure.

    Args:
        display_index: The index of the display to check.
        color: Optional RGB color to check against the screenshot. If provided,
               the function verifies that the screenshot matches this color.
               If None, it will only check that the screenshot is not black.

    Returns:
        True if the screenshot is valid (not black or matches the expected color).

    Raises:
        ValueError: If the screenshot does not match the expected color or is black.
    """
    logging.debug(f"Checking screenshot for display {display_index}")
    screenshot_bmp = self._ucd_manager.get_screenshot_display(display_index)
    screenshot_raw = image.process_bmp_img_to_raw(screenshot_bmp)

    timestamp = int(time.time())
    if color:
      filename = f"display_{display_index}_{color}_{timestamp}_raw.bmp"
      if not image.check_rgb_image_matches_color(screenshot_raw, color):
        self._save_screenshot(screenshot_bmp, filename)
        raise ValueError(f"Screenshot for display {display_index} does not match the expected color {color}. Saved to {filename}.")
      logging.info(f"Screenshot for display {display_index} matches the expected color {color}.")
    else:
      filename = f"display_{display_index}_{timestamp}_raw.bmp"
      if not image.is_rgb_image_not_black(screenshot_raw):
        self._save_screenshot(screenshot_bmp, filename)
        raise ValueError(f"Screenshot for display {display_index} is black. Saved to {filename}.")
      logging.info(f"Screenshot for display {display_index} is not black.")

  def _save_screenshot(self, data: bytes, filename: str):
    """Saves binary data to a file in the test's log directory.

    Args:
        data: The binary data to save
        filename: The name of the file to create
    """
    filepath = os.path.join(self.log_path, filename)
    logging.info(f"Saving screenshot to {filepath}")

    with open(filepath, "wb") as f:
      f.write(data)

  def _perform_sanity_check(self):
    """Performs a sanity check on the DUT and UCD."""
    logging.debug("performing sanity check..")
    self._ucd_manager.unplug_and_destroy_all_displays()
    self._ucd_manager.plug_additional_displays_to_active_displays(1)
    self._ucd_manager.unplug_and_destroy_all_displays()
