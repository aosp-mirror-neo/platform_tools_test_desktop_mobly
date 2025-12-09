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
from display.utils import modetest_helper
from display.utils import platform_info_helper
from display.utils import ucd_test_base
from mobly import asserts
from mobly import base_suite
from mobly import config_parser
from mobly import suite_runner


class BwWithDisplaysTest(ucd_test_base.UcdTestBase):
  """Test class for testing the system bandwidth with multiple displays."""

  def test_connected_display_max_bw(self):
    """Test class for testing the connected Display Max BW."""
    asserts.skip_if(
        self._ucd_manager.interface_type != interface_types.InterfaceType.DP,
        "This test is only applicable to DP displays.",
    )

    original_spec, original_dsc = self._ucd_manager.get_dp_video_spec()
    try:
      # Setup UCD as a sink with required max resolution per board
      board_name = platform_info_helper.get_current_board_name(self.dut)
      board_caps = board_capabilities.get_board_display_capabilities(board_name)
      asserts.assert_true(
          board_caps,
          f"No Display Capabilities found for board: '{board_name}'",
      )

      self._ucd_manager.set_dp_video_spec(
          board_caps.dp_spec, dsc=board_caps.dsc
      )
      edid_for_max_mode = board_caps.edid_for_max_mode

      self._ucd_manager.replug_displays(
          display_count=1,
          wait_for_active=True,
          displays_edids=[edid_for_max_mode.Edid],
      )
      streams = self._ucd_manager.get_active_displays()
      asserts.assert_equal(
          len(streams),
          1,
          "Number of valid streams do not match the number of ext displays"
          " connected: 1",
      )

      # Verify the EDID on the connector matches what we expect.
      _, connectors = modetest_helper.get_all_connectors_props(self.dut)
      dut_edid = None
      for _, props in connectors.items():
        if props["connected"] and props["name"].startswith("DP"):
          dut_edid = props["props"].get("EDID")
          break
      asserts.assert_is_not_none(
          dut_edid, "Could not find EDID for connected DP."
      )
      expected_edid = "".join(edid_for_max_mode.Edid.edid_hex_string.split())
      asserts.assert_equal(
          dut_edid.lower(),
          expected_edid.lower(),
          "DUT EDID does not match the expected EDID. DUT EDID: "
          f"{dut_edid}, Expected EDID: {expected_edid}",
      )

      requested_hactive = edid_for_max_mode.Hactive
      requested_vactive = edid_for_max_mode.Vactive
      requested_frame_rate_mhz = edid_for_max_mode.RefreshRate * 1000
      refresh_rate_tolerance_mhz = (
          edid_for_max_mode.refresh_rate_tolerance_hz * 1000
      )

      frame_rate_in_range = (
          abs(streams[0].frame_rate - requested_frame_rate_mhz)
          <= refresh_rate_tolerance_mhz
      )

      asserts.assert_true(
          streams[0].hactive == requested_hactive
          and streams[0].vactive == requested_vactive
          and frame_rate_in_range,
          "External display is not active with requested timings.\n"
          f"Requested: Hactive={requested_hactive},"
          f" Vactive={requested_vactive}, Refresh Rate"
          f" ~{edid_for_max_mode.RefreshRate}Hz"
          f" (+/- {edid_for_max_mode.refresh_rate_tolerance_hz}Hz)\n"
          f"Actual: Hactive={streams[0].hactive},"
          f" Vactive={streams[0].vactive}, Refresh Rate="
          f"{streams[0].frame_rate / 1000.0:.2f}Hz"
          f" ({streams[0].frame_rate}mHz)",
      )

      self.check_all_screenshots_for_displays(1)
    finally:
      self._ucd_manager.set_dp_video_spec(original_spec, original_dsc)


class BwWithDisplaysTestSuite(base_suite.BaseSuite):
  """Test suite for testing the system bandwidth with displays."""

  def setup_suite(self, _config: config_parser.TestRunConfig):
    self.add_test_class(BwWithDisplaysTest)


def main() -> None:
  suite_runner.run_suite_class()


if __name__ == "__main__":
  main()
