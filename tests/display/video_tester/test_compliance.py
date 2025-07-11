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

from typing import Optional

from display.utils import compliance_tests_manager
from display.utils import interface_types
from display.utils import ucd_base_test
from display.utils import ucd_compliance_tests_lists
from mobly import asserts
from mobly import base_suite
from mobly import config_parser
from mobly import suite_runner


class ComplianceTest(ucd_base_test.UcdBaseTest):
  """Test class for running VESA compliance tests."""

  def pre_run(self):
    self.setup_generated_tests()

  def setup_class(self):
    super().setup_class()

  def _run_compliance_test(
      self, test_list, restrict_interface_type, test_name, test_filter=None
  ):
    if restrict_interface_type is not None:
      asserts.skip_if(
          self._ucd_manager.interface_type != restrict_interface_type,
          "This test is only applicable to"
          f" {restrict_interface_type} displays.",
      )

    asserts.assert_true(
        self._ucd_manager.run_compliance_tests(test_list, test_filter),
        f"{test_name} Failed.",
    )

  def setup_generated_tests(self):
    """Sets up the generated test cases for compliance testing.

    This method defines a list of test configurations, where each configuration
    is a tuple containing:
    1. The compliance test group to run.
    2. An optional interface type restriction (e.g., DP, HDMI). If None, the
       test runs regardless of the interface type.
    3. A descriptive name for the test case.
    4. An optional list of specific subtest filters within the group.
    """
    tests: list[
        tuple[
            compliance_tests_manager.TestGroup,
            Optional[interface_types.InterfaceType],
            str,
            Optional[list[str]],
        ]
    ] = [
        (
            ucd_compliance_tests_lists.PIXEL_LEVEL_VIDEO_TEST,
            None,
            "Pixel Level Video Test",
        ),
        (
            ucd_compliance_tests_lists.CRC_BASED_VIDEO_TEST_SET,
            interface_types.InterfaceType.DP,
            "DP CRC Based Video Test",
        ),
        (ucd_compliance_tests_lists.LINK_TEST_SET, None, "Link Test"),
        (
            ucd_compliance_tests_lists.DP_1_4_LL_CTS,
            interface_types.InterfaceType.DP,
            "DP 1.4 Link Layer CTS 4.2.1.x",
            ["4.2.1"],
        ),
        (
            ucd_compliance_tests_lists.DP_1_4_LL_CTS,
            interface_types.InterfaceType.DP,
            "DP 1.4 Link Layer CTS 4.2.2.x",
            ["4.2.2"],
        ),
        (
            ucd_compliance_tests_lists.DP_1_4_LL_CTS,
            interface_types.InterfaceType.DP,
            "DP 1.4 Link Layer CTS 4.3.1.x",
            ["4.3.1"],
        ),
        (
            ucd_compliance_tests_lists.DP_1_4_LL_CTS,
            interface_types.InterfaceType.DP,
            "DP 1.4 Link Layer CTS 4.3.2.x and/or 4.3.3.1",
            ["4.3.2", "4.3.3.1"],
        ),
        (
            ucd_compliance_tests_lists.DP_1_4_LL_CTS,
            interface_types.InterfaceType.DP,
            "DP 1.4 Link Layer CTS 4.4.(1/2/3)",
            ["4.4.1", "4.4.2", "4.4.3"],
        ),
        (
            ucd_compliance_tests_lists.DP_1_4_LL_CTS,
            interface_types.InterfaceType.DP,
            "DP 1.4 Link Layer CTS 4.4.4.x",
            ["4.4.4"],
        ),
        (
            ucd_compliance_tests_lists.DP_1_4_LL_CTS,
            interface_types.InterfaceType.DP,
            "DP 1.4 Link Layer CTS 4.5",
            ["4.5"],
        ),
        (
            ucd_compliance_tests_lists.DP_1_4_DSC_LL_CTS,
            interface_types.InterfaceType.DP,
            "DP 1.4 DSC Link Layer CTS",
        ),
        (
            ucd_compliance_tests_lists.DP_1_4_DISPLAYID_CTS_SOURCE_TEST_SET,
            interface_types.InterfaceType.DP,
            "DP 1.4 DisplayID CTS Source Test Set",
        ),
        (
            ucd_compliance_tests_lists.HDMI_RX_CRC_TEST_SET,
            interface_types.InterfaceType.HDMI,
            "HDMI RX CRC Test",
        ),
        (
            ucd_compliance_tests_lists.HDMI_RX_VRR_TEST_SET,
            interface_types.InterfaceType.HDMI,
            "HDMI RX VRR Test",
        ),
    ]

    self.generate_tests(
        test_logic=self._run_compliance_test,
        name_func=lambda test_list, restrict_interface_type, test_name, test_filter=None: f"test_{test_name.lower().replace(' ', '_')}",
        arg_sets=tests,
    )


class ComplianceTestSuite(base_suite.BaseSuite):
  """Compliance Test Suite."""

  def setup_suite(self, config: config_parser.TestRunConfig):
    self.add_test_class(ComplianceTest)


def main() -> None:
  suite_runner.run_suite_class()


if __name__ == "__main__":
  main()
