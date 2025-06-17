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

"""Testing the System Bandwidth in supporting displays."""

from display.utils import interface_types
from display.utils import ucd_base_test
from lib.pasit.passport import passport_host
from lib.utils import retry

from mobly import asserts
from mobly import base_suite
from mobly import config_parser
from mobly import suite_runner

PassportBaseError = passport_host.PassportBaseError


class BwWithDisplaysTest(ucd_base_test.UcdBaseTest):
  """Test class for testing the system bandwidth with multiple displays.

  This class includes tests to verify the system's ability to handle an
  increasing and decreasing number of displays, ensuring that each display is
  correctly activated and managed.
  """

  def pre_run(self):
    displays_range_arg_sets = [
        (i,)
        for i in range(1, self._UCD_ABSOLUTE_MAX_CONNECTED_DISPLAYS + 1)
    ]

    self.generate_tests(
        test_logic=self.plug_n_at_once,
        name_func=self.generate_test_name_plug_n_at_once,
        arg_sets=displays_range_arg_sets,
    )

    self.generate_tests(
        test_logic=self.increment_displays,
        name_func=self.generate_test_name_increment_displays,
        arg_sets=displays_range_arg_sets,
    )

    self.generate_tests(
        test_logic=self.decrement_displays,
        name_func=self.generate_test_name_decrement_displays,
        arg_sets=displays_range_arg_sets,
    )

    self.generate_tests(
        test_logic=self.toggle_mst_and_sbm,
        name_func=self.generate_test_name_toggle_mst_sbm,
        arg_sets=[(False, False), (False, True), (True, False), (True, True)],
    )

  def generate_test_name_increment_displays(self, display_count: int) -> str:
    """Generates the test name for incrementing displays to a specific count."""
    return f"test_increment_displays_to_{display_count}_displays"

  def generate_test_name_decrement_displays(self, display_count: int) -> str:
    """Generates the test name for decrementing displays to a specific count."""
    return f"test_decrement_displays_from_{display_count}_displays"

  def generate_test_name_plug_n_at_once(self, display_count: int) -> str:
    """Generates the test name for plugging in and out displays at once."""
    return f"test_plug_{display_count}_displays_at_once"

  def generate_test_name_toggle_mst_sbm(self, is_mst: bool, is_sbm: bool) -> str:
    """Generates the test name for toggling MST and SBM."""
    return f"test_toggle_mst_{is_mst}_sbm_{is_sbm}"

  def increment_displays(self, display_count: int):
    """Tests the system's ability to handle an increasing number of displays.

    This test gradually increases the number of attached displays by one,
    verifying that the system can successfully activate and manage each
    additional display.

    Args:
        max_display_count: The maximum number of displays to test up to.
    """

    self.skip_if_display_count_not_supported(display_count)

    for i in range(display_count):
      display_count_to_test = i + 1
      self._ucd_manager.plug_additional_displays_to_active_displays(
          additional_display_count=1
      )
      self.check_all_screenshots_for_displays(display_count_to_test)

  def decrement_displays(self, display_count: int):
    """Tests the system's ability to handle a decreasing number of displays.

    This test starts with the maximum number of supported displays, then
    gradually removes one display at a time, verifying that the system
    continues to function correctly with each reduction in the number of
    active displays.

    Args:
        max_display_count: The maximum number of displays to test up to.
    """
    self.skip_if_display_count_not_supported(display_count)

    self._ucd_manager.plug_additional_displays_to_active_displays(
        display_count
    )

    for i in range(display_count, 0, -1):
      self.check_all_screenshots_for_displays(i)

      self._ucd_manager.destroy_the_most_recently_attached_display()

  def plug_n_at_once(self, display_count: int):
    """Tests the system's ability to plug in and out displays at once."""

    self.skip_if_display_count_not_supported(display_count)

    self._ucd_manager.plug_additional_displays_to_active_displays(
        additional_display_count=display_count)
    self.check_all_screenshots_for_displays(display_count)

    self._ucd_manager.unplug_and_destroy_all_displays()

  def toggle_mst_and_sbm(self, is_mst: bool, is_sbm: bool):
    """Tests the system's ability to toggle MST and SBM."""
    asserts.skip_if(
        self._ucd_manager.interface_type != interface_types.InterfaceType.DP,
        "This test is only applicable to DP displays.",
    )

    self._ucd_manager.unplug_and_destroy_all_displays()

    if not self.passport_host.video_tester_client.set_dp_link_capabilities(
        mst=is_mst,
        ss_sbm=is_sbm,
        mst_sink_count=1,
    ):
      raise PassportBaseError("Failed to set DP link capabilities.")
    if not self.passport_host.video_tester_client.perform_attach_operation(True):
      raise PassportBaseError("Failed to attach to the DUT.")

    asserts.assert_true(
        self._ucd_manager.are_displays_reporting_stream_info(1),
        f"External displays is not active with MST={is_mst} and SBM={is_sbm}.",
    )
    retry.retry(func=lambda: self.check_all_screenshots_for_displays(1), max_tries=5)


class BwWithDisplaysTestSuite(base_suite.BaseSuite):
  """Test suite for testing the system bandwidth with displays."""

  def setup_suite(self, config: config_parser.TestRunConfig):
    self.add_test_class(BwWithDisplaysTest)


def main() -> None:
  suite_runner.run_suite_class()

if __name__ == "__main__":
  main()
