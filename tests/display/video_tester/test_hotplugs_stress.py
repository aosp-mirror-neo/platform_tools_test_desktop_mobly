# Copyright 2026 Google LLC
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

"""Testing hotplug stress functionalities."""

import logging
import time

from display.utils import ucd_test_base
from mobly import asserts
from mobly import base_suite
from mobly import config_parser
from mobly import suite_runner


class HotplugsStressTest(ucd_test_base.UcdTestBase):
  """Test class for testing hotplug functionalities (stress)."""

  _STRESS_ITERATION_COUNT = 77

  def pre_run(self):
    for display_count in range(
        1, self._UCD_ABSOLUTE_MAX_CONNECTED_DISPLAYS + 1
    ):
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

  def hotplug_unplug_stress(self, iteration_count: int, display_count: int):
    """Stress tests plugging and unplugging displays."""

    self.skip_if_display_count_not_supported(display_count)

    for i in range(iteration_count):
      logging.info("Hotplug cycle %d/%d", i + 1, iteration_count)
      self._ucd_manager.replug_displays(
          display_count=display_count, wait_for_active=True
      )
      asserts.assert_true(
          self._ucd_manager.wait_for_display_count(display_count),
          f"Expected {display_count} displays to be active.",
      )
      self._ucd_manager.unplug_all_displays(wait_for_active=True)
      asserts.assert_true(
          self._ucd_manager.wait_for_display_count(0),
          "Expected 0 displays to be active.",
      )

      self.rotate_event_capture()

  def hpd_storm_test(self, iteration_count: int, display_count: int):
    """Stress tests by sending continuous HPD signals."""

    self.skip_if_display_count_not_supported(display_count)

    self._ucd_manager.replug_displays(
        display_count=display_count, wait_for_active=True
    )
    asserts.assert_true(
        self._ucd_manager.wait_for_display_count(display_count),
        f"Expected {display_count} displays to be active.",
    )

    for i in range(iteration_count):
      logging.info("HPD cycle %d/%d", i + 1, iteration_count)
      self._ucd_manager.send_hpd_pulse()
      time.sleep(0.05)

    # Let the dust settle then check.
    time.sleep(5)
    asserts.assert_true(
        self._ucd_manager.wait_for_display_count(display_count),
        f"Expected {display_count} displays to be active.",
    )


class HotplugsStressTestSuite(base_suite.BaseSuite):
  """Test suite for testing hotplug functionalities (stress)."""

  def setup_suite(self, config: config_parser.TestRunConfig):
    self.add_test_class(HotplugsStressTest)


def main() -> None:
  suite_runner.run_suite_class()


if __name__ == "__main__":
  main()
