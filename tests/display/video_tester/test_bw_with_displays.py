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


from display.utils import board_capabilities
from display.utils import interface_types
from display.utils import platform_info_helper
from display.utils import ucd_base_test
from mobly import asserts
from mobly import base_suite
from mobly import config_parser
from mobly import suite_runner


class BwWithDisplaysTest(ucd_base_test.UcdBaseTest):
  """Test class for testing the system bandwidth with multiple displays."""

  def test_connected_display_max_bw(self):
    """Test class for testing the connected Display Max BW."""
    asserts.skip_if(
        self._ucd_manager.interface_type != interface_types.InterfaceType.DP,
        "This test is only applicable to DP displays.",
    )

    # Setup UCD as a sink with required max resolution per board
    board_name = platform_info_helper.get_current_board_name(self.dut)
    edid_for_max_mode = (
        board_capabilities.get_edid_for_max_supported_res_for_board(board_name)
    )
    asserts.assert_true(
        edid_for_max_mode,
        f"No Edid for Max Resolution found for board: '{board_name}'",
    )

    self._ucd_manager.plug_additional_displays_to_active_displays(
        additional_display_count=1, displays_edids=[edid_for_max_mode.Edid]
    )
    streams = self._ucd_manager.get_valid_streams()
    asserts.assert_equal(
        len(streams),
        1,
        f"Number of valid streams do not match the number of ext displays"
        f" connected: 1",
    )

    requested_hactive = edid_for_max_mode.Hactive
    requested_vactive = edid_for_max_mode.Vactive
    requested_frame_rate = edid_for_max_mode.RefreshRate

    asserts.assert_true(
        streams[0].hactive == requested_hactive
        and streams[0].vactive == requested_vactive
        and streams[0].frame_rate == requested_frame_rate,
        f"""External display is not active with requested Hactive = {requested_hactive} or
      requested Vactive = {requested_vactive} or requested Frame Rate = {requested_frame_rate}
      Current timings are: Hactive = {streams[0].hactive} Vactive = {streams[0].vactive}
      Frame Rate = {streams[0].frame_rate}""",
    )


class BwWithDisplaysTestSuite(base_suite.BaseSuite):
  """Test suite for testing the system bandwidth with displays."""

  def setup_suite(self, _config: config_parser.TestRunConfig):
    self.add_test_class(BwWithDisplaysTest)


def main() -> None:
  suite_runner.run_suite_class()


if __name__ == "__main__":
  main()
