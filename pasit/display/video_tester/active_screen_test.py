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

"""Testing if the screen is active with Video Tester."""

from mobly import asserts
from mobly import test_runner

from pasit.display.utils import ucd_manager
from pasit.lib import pasit_test


class ConnectedDisplayActiveTest(pasit_test.PasitTestClass):
  """Test class for testing active screens with Video Tester."""

  ucd_manager: ucd_manager.UcdManager

  def pre_run(self):
    self.generate_tests(
        test_logic=self.active_screen_with_tester_state,
        name_func=self.generate_test_name_with_tester_state,
        arg_sets=[(1,), (2,), (3,)],
    )
    self.generate_tests(
        test_logic=self.active_screen_with_screenshot_check,
        name_func=self.generate_test_name_with_screenshot_check,
        arg_sets=[(1,), (2,)],
    )

  def setup_class(self):
    super().setup_class()
    self.video_tester_client = self.passport_host.video_tester_client
    self.ucd_manager = ucd_manager.UcdManager(
        self.video_tester_client
    )
    self.ucd_manager.connect_to_ucd()
    self.ucd_manager.reset_ucd_displays_state_to_default()

  def teardown_class(self):
    self.ucd_manager.disconnect_ucd()

  def teardown_test(self):
    self.ucd_manager.reset_ucd_displays_state_to_default()

  def generate_test_name_with_tester_state(self, display_count: int) -> str:
    return f"test_active_screen_with_{display_count}_displays_with_tester_state"

  def generate_test_name_with_screenshot_check(self, display_index: int) -> str:
    return f"test_active_screen_with_screenshot_check_display_{display_index}"

  def active_screen_with_tester_state(self, display_count: int):
    self.ucd_manager.create_and_plug_new_displays(display_count)
    asserts.assert_true(
        self.ucd_manager.are_all_screens_on_aux_channel(display_count),
        "External displays are not active."
    )

  def active_screen_with_screenshot_check(self, display_count: int):
    self.ucd_manager.create_and_plug_new_displays(display_count)
    self.ucd_manager.are_all_screens_on_aux_channel(display_count)
    for i in range(display_count):
      print(f"Checking screenshot for display {i}")
      screenshot = self.ucd_manager.get_screenshot_display(i)
      asserts.assert_true(
          self.ucd_manager.is_image_not_black(screenshot),
          f"Screenshot for display {i} is black.",
      )

if __name__ == "__main__":
  test_runner.main()
