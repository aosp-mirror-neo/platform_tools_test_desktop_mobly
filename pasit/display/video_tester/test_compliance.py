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

"""Run VESA compliance tests using UCD."""

from mobly import asserts
from mobly import test_runner

from pasit.display.utils import ucd_compliance_tests_lists
from pasit.display.utils import ucd_manager
from pasit.lib import pasit_test


class ComplianceTest(pasit_test.PasitTestClass):
  """Test class for running VESA compliance tests."""

  def setup_class(self):
    super().setup_class()
    self.video_tester_client = self.passport_host.video_tester_client
    self.ucd_manager = ucd_manager.UcdManager(self.video_tester_client)
    self.ucd_manager.connect_to_ucd()
    self.ucd_manager.reset_ucd_displays_state_to_default()

  def teardown_class(self):
    self.ucd_manager.disconnect_ucd()

  def teardown_test(self):
    self.ucd_manager.reset_ucd_displays_state_to_default()

  def test_dp_1_4_link_layer_cts(self):
    asserts.assert_true(
        self.ucd_manager.run_compliance_tests(
            ucd_compliance_tests_lists.DP_1_4_LL_CTS,
            ["4.2.1", "4.2.2.3", "4.5"],
        ),
        "DP 1.4 Link Layer CTS Failed.",
    )

  def test_pixel_level_video_test(self):
    asserts.assert_true(
        self.ucd_manager.run_compliance_tests(
            ucd_compliance_tests_lists.PIXEL_LEVEL_VIDEO_TEST
        ),
        "Pixel Level Video Test Failed.",
    )


if __name__ == "__main__":
  test_runner.main()
