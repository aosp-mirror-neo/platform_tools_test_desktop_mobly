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

"""Testing hotplug functionalities."""

import logging
import time

from display.utils import interface_types
from display.utils import ucd_base_test
from mobly import asserts
from mobly import base_suite
from mobly import config_parser
from mobly import suite_runner


class HotplugsTest(ucd_base_test.UcdBaseTest):
  """Test class for testing hotplug functionalities."""

  _STRESS_ITERATION_COUNT = 77

  def pre_run(self):
    for display_count in range(
        1, self._UCD_ABSOLUTE_MAX_CONNECTED_DISPLAYS + 1
    ):
      self.generate_tests(
          test_logic=self.plug_n_at_once,
          name_func=self.generate_test_name_plug_n_at_once,
          arg_sets=[(display_count,)],
      )

      # TODO: b/391360720 - Because this test uses the highest number of
      # displays supported, it will fail because we don't support all support
      # displays. So generate tests now to start at different starting counts to
      # get some signals. Once we officially support all displays, this can be a
      # static test starting at self.max_tested_displays.
      self.generate_tests(
          test_logic=self.increment_displays,
          name_func=self.generate_test_name_increment_displays,
          arg_sets=[(display_count,)],
      )

      self.generate_tests(
          test_logic=self.decrement_displays,
          name_func=self.generate_test_name_decrement_displays,
          arg_sets=[(display_count,)],
      )

      self.generate_tests(
          test_logic=self.reboot_with_displays_plugged,
          name_func=self.generate_test_name_reboot_with_displays_plugged,
          arg_sets=[(display_count,)],
      )

      self.generate_tests(
          test_logic=self.hotplug_unplug_stress,
          name_func=self.generate_test_name_hotplug_unplug_stress,
          arg_sets=[(self._STRESS_ITERATION_COUNT, display_count)],
      )

      self.generate_tests(
          test_logic=self.hpd_storm_test,
          name_func=self.generate_test_name_hpd_storm_test,
          arg_sets=[(self._STRESS_ITERATION_COUNT, display_count)],
      )

      self.generate_tests(
          test_logic=self.hotplug_under_cpu_load,
          name_func=self.generate_test_name_hotplug_under_cpu_load,
          arg_sets=[(display_count,)],
      )

  def generate_test_name_plug_n_at_once(self, display_count: int) -> str:
    """Generates the test name for plugging in and out displays at once."""
    return f"test_plug_{display_count}_displays_at_once"

  def generate_test_name_increment_displays(self, display_count: int) -> str:
    """Generates the test name for incrementing displays to a specific count."""
    return f"test_increment_displays_to_{display_count}_displays"

  def generate_test_name_decrement_displays(self, display_count: int) -> str:
    """Generates the test name for decrementing displays to a specific count."""
    return f"test_decrement_displays_from_{display_count}_displays"

  def generate_test_name_reboot_with_displays_plugged(self, display_count: int):
    """Generates test name for reboot with displays plugged test."""
    display_str = f"{display_count}_display{'s' if display_count > 1 else ''}"
    return f"test_reboot_with_{display_str}_plugged"

  def generate_test_name_hotplug_unplug_stress(
      self, iteration_count: int, display_count: int
  ):
    """Generates the test name for hotplug/unplug stress test."""
    display_str = f"{display_count}_display{'s' if display_count > 1 else ''}"
    return (
        f"test_hotplug_unplug_stress_{display_str}_{iteration_count}_iterations"
    )

  def generate_test_name_hpd_storm_test(
      self, iteration_count: int, display_count: int
  ):
    """Generates the test name for HPD storm test."""
    display_str = f"{display_count}_display{'s' if display_count > 1 else ''}"
    return f"test_hpd_storm_{display_str}_{iteration_count}_iterations"

  def generate_test_name_hotplug_under_cpu_load(
      self, display_count: int
  ) -> str:
    """Generates test name for hotplug under high CPU load test."""
    display_str = f"{display_count}_display{'s' if display_count > 1 else ''}"
    return f"test_hotplug_{display_str}_under_cpu_load"

  def plug_n_at_once(self, display_count: int):
    """Tests the system's ability to plug in and out displays at once."""

    self.skip_if_display_count_not_supported(display_count)

    self._ucd_manager.plug_additional_displays_to_active_displays(
        additional_display_count=display_count, force_mst=display_count > 1
    )
    self.check_all_screenshots_for_displays(display_count)

  def increment_displays(self, display_count: int):
    """Tests the system's ability to handle an increasing number of displays.

    This test gradually increases the number of attached displays by one,
    verifying that the system can successfully activate and manage each
    additional display.

    Args:
        display_count: The maximum number of displays to test up to.
    """
    asserts.skip_if(
        self._ucd_manager.interface_type != interface_types.InterfaceType.DP,
        "This test is only applicable to DP displays.",
    )
    self.skip_if_display_count_not_supported(display_count)
    asserts.skip_if(
        display_count < 2,
        "This test requires at least 2 displays.",
    )

    for i in range(display_count):
      display_count_to_test = i + 1
      logging.info("Plugging in %d displays.", display_count_to_test)
      self._ucd_manager.plug_additional_displays_to_active_displays(
          additional_display_count=1,
          force_mst=True,
      )
      self.check_all_screenshots_for_displays(display_count_to_test)

  def decrement_displays(self, display_count: int):
    """Tests the system's ability to handle a decreasing number of displays.

    This test starts with the maximum number of supported displays, then
    gradually removes one display at a time, verifying that the system
    continues to function correctly with each reduction in the number of
    active displays.

    Args:
        display_count: The maximum number of displays to test up to.
    """
    asserts.skip_if(
        self._ucd_manager.interface_type != interface_types.InterfaceType.DP,
        "This test is only applicable to DP displays.",
    )
    self.skip_if_display_count_not_supported(display_count)
    asserts.skip_if(
        display_count < 2,
        "This test requires at least 2 displays.",
    )

    # Plug in all available displays to start unplugging them one by one.
    self._ucd_manager.plug_additional_displays_to_active_displays(
        display_count,
        force_mst=True,
    )

    for i in range(display_count, 0, -1):
      self.check_all_screenshots_for_displays(i)

      self._ucd_manager.destroy_the_most_recently_attached_display(
          force_mst=True
      )

  def reboot_with_displays_plugged(self, display_count: int):
    """Tests rebooting the device with displays already connected."""

    self.skip_if_display_count_not_supported(display_count)

    self._ucd_manager.plug_additional_displays_to_active_displays(
        display_count, force_mst=(display_count > 1)
    )
    self._check_for_displays_on(display_count)

    logging.info("Rebooting DUT.")
    self.dut.reboot()
    # Give time for the device to reboot and settle.
    time.sleep(10)

    logging.info("DUT rebooted. Verifying displays are active.")
    self._check_for_displays_on(display_count)

  def hotplug_unplug_stress(self, iteration_count: int, display_count: int):
    """Stress tests plugging and unplugging displays."""

    self.skip_if_display_count_not_supported(display_count)

    for i in range(iteration_count):
      logging.info("Hotplug cycle %d/%d", i + 1, iteration_count)
      self._ucd_manager.plug_additional_displays_to_active_displays(
          display_count
      )
      self._check_for_displays_on(display_count)
      self._ucd_manager.unplug_and_destroy_all_displays()
      self._check_for_displays_on(0)

  def hpd_storm_test(self, iteration_count: int, display_count: int):
    """Stress tests by sending continuous HPD signals."""

    self.skip_if_display_count_not_supported(display_count)

    self._ucd_manager.plug_additional_displays_to_active_displays(display_count)
    self._check_for_displays_on(display_count)

    for i in range(iteration_count):
      logging.info("HPD cycle %d/%d", i + 1, iteration_count)
      self._ucd_manager.send_hpd_pulse()
      time.sleep(0.05)

    # Let the dust settle then check.
    time.sleep(5)
    self._check_for_displays_on(display_count)

  def hotplug_under_cpu_load(self, display_count: int):
    """Tests hotplugging displays while the DUT is under high CPU load."""

    self.skip_if_display_count_not_supported(display_count)

    num_cores_str = self.dut.shell(["nproc"]).decode("utf-8").strip()
    num_cores = int(num_cores_str) if num_cores_str.isdigit() else 1

    logging.info("Starting %d CPU stress processes.", num_cores)
    self.dut.shell([
        "sh",
        "-c",
        f"for i in $(seq {num_cores}); do while true; do :; done & done",
    ])
    time.sleep(5)  # Let CPU load ramp up

    try:
      logging.info("Performing hotplug/unplug under CPU load.")
      self._ucd_manager.plug_additional_displays_to_active_displays(
          display_count
      )
      self._check_for_displays_on(display_count)
      self._ucd_manager.unplug_and_destroy_all_displays()
      self._check_for_displays_on(0)
    finally:
      logging.info("Stopping CPU stress processes.")
      self.dut.shell(["pkill", "-f", "while true; do :; done"])

  def _check_for_displays_on(self, display_count: int):
    asserts.assert_true(
        self._ucd_manager.are_displays_reporting_stream_info(display_count),
        f"External displays are not active for {display_count} displays.",
    )
    asserts.assert_true(
        self.dut.is_device_online(), "Device is not reporting online."
    )
    self.check_all_screenshots_for_displays(display_count)


class HotplugsTestSuite(base_suite.BaseSuite):
  """Test suite for testing hotplug functionalities."""

  def setup_suite(self, config: config_parser.TestRunConfig):
    self.add_test_class(HotplugsTest)


def main() -> None:
  suite_runner.run_suite_class()


if __name__ == "__main__":
  main()
