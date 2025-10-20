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

"""Testing low level MST features."""

import time

from display.utils import interface_types
from display.utils import ucd_base_test
from mobly import asserts
from mobly import base_suite
from mobly import config_parser
from mobly import signals
from mobly import suite_runner


class MstTest(ucd_base_test.UcdBaseTest):
  """Test class for testing low level MST features."""

  def pre_run(self):
    self.generate_tests(
        test_logic=self.toggle_mst_and_sbm,
        name_func=self.generate_test_name_toggle_mst_sbm,
        arg_sets=[(False, False), (False, True), (True, False), (True, True)],
    )

  def set_up_class(self):
    super().set_up_class()
    asserts.skip_if(
        self._ucd_manager.interface_type != interface_types.InterfaceType.DP,
        "This test is only applicable to DP displays.",
    )

  def generate_test_name_toggle_mst_sbm(
      self, is_mst: bool, is_sbm: bool
  ) -> str:
    """Generates the test name for toggling MST and SBM."""
    return f"test_toggle_mst_{is_mst}_sbm_{is_sbm}"

  def toggle_mst_and_sbm(self, is_mst: bool, is_sbm: bool):
    """Tests the system's ability to toggle MST and SBM."""

    self._ucd_manager.unplug_and_destroy_all_displays()

    if not self.passport_host.video_tester_client.set_dp_link_capabilities(
        mst=is_mst,
        ss_sbm=is_sbm,
        mst_sink_count=1,
    ):
      raise signals.TestError("Failed to set DP link capabilities.")
    time.sleep(5)
    if not self.passport_host.video_tester_client.perform_attach_operation(
        True
    ):
      raise signals.TestError("Failed to attach to the DUT.")
    time.sleep(5)

    asserts.assert_true(
        self._ucd_manager.are_displays_reporting_stream_info(1),
        f"External displays is not active with MST={is_mst} and SBM={is_sbm}.",
    )
    self.check_all_screenshots_for_displays(1)


class MstTestSuite(base_suite.BaseSuite):
  """Test suite for testing low level MST features."""

  def setup_suite(self, _: config_parser.TestRunConfig):
    self.add_test_class(MstTest)


if __name__ == "__main__":
  suite_runner.run_suite_class()
