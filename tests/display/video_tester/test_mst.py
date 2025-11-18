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

import logging
import time

from display.utils import interface_types
from display.utils import modetest_helper
from display.utils import ucd_test_base
from lib.pasit.passport import errors
from mobly import asserts
from mobly import base_suite
from mobly import config_parser
from mobly import suite_runner

PassportBaseError = errors.PassportBaseError


class MstTest(ucd_test_base.UcdTestBase):
  """Test class for testing low level MST features."""

  cached_modetest_output: str | None = None

  def pre_run(self):
    for display_count in range(
        1, self._UCD_ABSOLUTE_MAX_CONNECTED_DISPLAYS + 1
    ):
      self.generate_tests(
          test_logic=self.path_prop,
          name_func=self.generate_test_name_path_prop,
          arg_sets=[(display_count,)],
      )

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

  def on_fail(self, record):
    if self.cached_modetest_output:
      logging.info(
          "modetest -c output on failure:\n%s", self.cached_modetest_output
      )
    super().on_fail(record)

  def generate_test_name_path_prop(self, display_count: int) -> str:
    """Generates the test name for testing the PATH prop."""
    return f"test_path_prop_with_{display_count}_displays"

  def generate_test_name_toggle_mst_sbm(
      self, is_mst: bool, is_sbm: bool
  ) -> str:
    """Generates the test name for toggling MST and SBM."""
    return f"test_toggle_mst_{is_mst}_sbm_{is_sbm}"

  def path_prop(self, display_count: int):
    """Test that the PATH prop appears as a connector property when MST is enabled."""

    self.skip_if_display_count_not_supported(display_count)

    (
        self.cached_modetest_output,
        connectors_before,
    ) = modetest_helper.get_all_connectors_props(self.dut)
    active_connectors_before = {
        connector_id: connector_data
        for connector_id, connector_data in connectors_before.items()
        if connector_data["connected"]
    }
    logging.debug("active connectors: %s", active_connectors_before.keys())
    asserts.assert_equal(
        len(active_connectors_before),
        1,
        "Expecting nothing connected but eDP. Instead, found %s."
        % active_connectors_before.keys(),
    )
    edp_connector_id = list(active_connectors_before.keys())[0]

    self._ucd_manager.replug_displays(
        display_count=display_count,
        wait_for_active=True,
        force_mst=True,
    )

    (
        self.cached_modetest_output,
        connectors_after,
    ) = modetest_helper.get_all_connectors_props(self.dut)
    active_connectors_after = {
        connector_id: connector_data
        for connector_id, connector_data in connectors_after.items()
        if connector_data["connected"]
    }
    logging.info(
        "active connectors after plugging in displays: %s",
        active_connectors_after.keys(),
    )

    mst_connector_ids = [
        connector_id
        for connector_id in active_connectors_after
        if connector_id != edp_connector_id
    ]
    asserts.assert_equal(
        len(mst_connector_ids),
        display_count,
        "Expecting %d MST connectors but found %s."
        % (display_count, mst_connector_ids),
    )

    base_connector_ids = set()
    downstream_ports = set()

    for mst_connector_id in mst_connector_ids:
      props = connectors_after[mst_connector_id]["props"]
      asserts.assert_in(
          "PATH",
          props,
          "Expecting PATH property to be present for MST parent connector but"
          " found %s." % props,
      )

      path_value = props["PATH"]
      logging.debug(
          "path_value for connector %d: %s", mst_connector_id, path_value
      )

      ascii_path_value = ""
      try:
        # The PATH value is a hex-encoded string.
        ascii_path_value = bytes.fromhex(path_value).decode("ascii")
      except (ValueError, UnicodeDecodeError) as e:
        asserts.fail(
            f"Failed to decode PATH property for connector {mst_connector_id}:"
            f" {path_value}. Error: {e}"
        )

      # Strip null characters.
      ascii_path_value = ascii_path_value.strip("\x00")
      asserts.assert_true(
          ascii_path_value,
          f"PATH property for connector {mst_connector_id} is empty after"
          " decoding and stripping null characters.",
      )

      # The format should be "mst:<base_connector_id>-<downstream_port>"
      # e.g. "mst:750-8"
      parts = ascii_path_value.split(":")
      asserts.assert_equal(
          len(parts),
          2,
          f"Unexpected PATH format for '{ascii_path_value}': expecting a single"
          " ':'.",
      )

      asserts.assert_equal(
          parts[0],
          "mst",
          f"Unexpected PATH prefix for '{ascii_path_value}': expecting 'mst'"
          f" but got '{parts[0]}'.",
      )

      id_port_parts = parts[1].split("-")
      asserts.assert_equal(
          len(id_port_parts),
          2,
          f"Unexpected PATH format for '{ascii_path_value}': expecting a single"
          " '-' after the colon.",
      )

      base_connector_id_str, downstream_port_str = id_port_parts
      asserts.assert_true(
          base_connector_id_str.isdigit(),
          f"Base connector ID in PATH '{ascii_path_value}' is not a valid"
          f" number: '{base_connector_id_str}'.",
      )
      asserts.assert_true(
          downstream_port_str.isdigit(),
          f"Downstream port in PATH '{ascii_path_value}' is not a valid"
          f" number: '{downstream_port_str}'.",
      )

      base_connector_id = int(base_connector_id_str)
      downstream_port = int(downstream_port_str)
      logging.debug(
          "Parsed MST path for connector %d: base_connector_id=%d,"
          " downstream_port=%d",
          mst_connector_id,
          base_connector_id,
          downstream_port,
      )
      base_connector_ids.add(base_connector_id)
      downstream_ports.add(downstream_port)

    asserts.assert_equal(
        len(base_connector_ids),
        1,
        "All MST connectors should have the same base connector ID, but found"
        " %s." % base_connector_ids,
    )

    asserts.assert_equal(
        len(downstream_ports),
        display_count,
        "Downstream ports should be unique, but found %s." % downstream_ports,
    )

    base_connector_id = base_connector_ids.pop()
    base_connector = connectors_after.get(base_connector_id)
    asserts.assert_is_not_none(
        base_connector,
        "Expecting base connector with ID %s to exist but it was not found."
        % base_connector_id,
    )
    asserts.assert_true(
        base_connector["name"].startswith("DP")
        or base_connector["name"].startswith("USB"),
        "Expecting base connector name to start with DP or USB but found %s."
        % base_connector["name"],
    )
    asserts.assert_true(
        not base_connector["connected"],
        "Expecting base connector to be disconnected but found %s."
        % base_connector["connected"],
    )

  def toggle_mst_and_sbm(self, is_mst: bool, is_sbm: bool):
    """Tests the system's ability to toggle MST and SBM."""

    self._ucd_manager.unplug_all_displays(wait_for_active=True)

    if not self.passport_host.video_tester_client.set_dp_link_capabilities(
        mst=is_mst,
        ss_sbm=is_sbm,
        mst_sink_count=1,
    ):
      raise PassportBaseError("Failed to set DP link capabilities.")
    time.sleep(5)
    if not self.passport_host.video_tester_client.perform_attach_operation(
        True
    ):
      raise PassportBaseError("Failed to attach to the DUT.")
    time.sleep(5)

    asserts.assert_true(
        self._ucd_manager.wait_for_display_count(1),
        f"External displays is not active with MST={is_mst} and SBM={is_sbm}.",
    )
    self.check_all_screenshots_for_displays(1)


class MstTestSuite(base_suite.BaseSuite):
  """Test suite for testing low level MST features."""

  def setup_suite(self, _: config_parser.TestRunConfig):
    self.add_test_class(MstTest)


if __name__ == "__main__":
  suite_runner.run_suite_class()
