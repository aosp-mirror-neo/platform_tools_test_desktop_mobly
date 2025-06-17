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

from display.utils import modetest_helper
from display.utils import ucd_manager
from lib.pasit import pasit_test
from lib.pasit.passport import passport_host

from mobly import asserts

PassportBaseError = passport_host.PassportBaseError


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
        self.passport_host.video_tester_client
    )
    self._ucd_manager.reset_ucd_displays_state_to_default()
    # Set the max number of displays that can be tested.
    max_crtc_on_dut = modetest_helper.get_crtcs_count(self.dut)
    theoritical_max_connected_displays = max_crtc_on_dut - 1  # 1 is used by eDP
    self.max_tested_displays = min(
        self._ucd_manager.max_supported_displays, theoritical_max_connected_displays
    )
    logging.info(f"max_tested_displays: {self.max_tested_displays}")
    asserts.assert_greater(
        self.max_tested_displays, 0,
        "No displays are supported by the system.",
    )

  def teardown_test(self):
    self._ucd_manager.reset_ucd_displays_state_to_default()
    if self.dut.is_servo_configured():
      self.dut.power_on_if_offline()

  def teardown_class(self):
    self._ucd_manager.disconnect_ucd()
    self.dut.reboot()

  def skip_if_display_count_not_supported(self, display_count: int):
    """Skips the test if the display count to test is greater than the maximum supported displays."""
    asserts.skip_if(
        display_count > self.max_tested_displays,
        f"{display_count} is greater than the maximum supported"
        f" {self.max_tested_displays}.",
    )

  def check_all_screenshots_for_displays(self, display_count: int)-> bool:
    """Checks if the screenshots of the displays are not black.

    This function iterates through the specified number of displays, takes a
    screenshot of each, and verifies that the screenshot is not a black image.
    A black screenshot indicates that the display is not active.

    Args:
        display_count: The number of displays to check.

    Returns:
        True if all screenshots are not black, throws an assertion error
        otherwise.
    """
    for i in range(display_count):
      logging.debug(f"Checking screenshot for display {i}")
      screenshot = self._ucd_manager.get_screenshot_display(i)
      asserts.assert_true(
          self._ucd_manager.is_image_not_black(screenshot),
          f"Screenshot for display {i} is black.",
      )
      logging.info(f"Screenshot for display {i} is not black.")

    return True
