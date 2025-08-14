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

"""Testing the suspend and resume functionality."""

import enum
import logging
import time

from display.utils import ucd_base_test
from lib.utils import image

from lib.pasit import dut_state_manager
from mobly import asserts
from mobly import base_suite
from mobly import config_parser
from mobly import suite_runner


class SuspendResumeTest(ucd_base_test.UcdBaseTest):
  """Test class for testing the suspend and resume functionality.

  This class includes tests for suspending and resuming the device with
  different suspend times and different stages of display plugging.
  It also includes stress tests to verify the stability of the suspend/resume
  functionality.
  """

  # TODO: b/422483099 - When we gain more confidence in our max display support,
  # replace this by self.max_tested_displays
  _PLUGGED_DISPLAYS = 1
  _SUSPEND_TIME_BASE = 1.5
  _MAX_SUSPEND_TIME_EXPONENT = 13
  _STESS_ITERATION_COUNT = 10

  class PlugInStage(enum.Enum):
    """Enum for the different phases of the suspend/resume test."""
    BEFORE_SUSPEND = 1
    DURING_SUSPEND = 2
    AFTER_SUSPEND = 3

  def pre_run(self):
    # Generate tests for suspend and resume with different stages of displays
    # plugging and different suspend times.
    self.generate_tests(
        test_logic=self.suspend_resume_with_plug,
        name_func=self.generate_test_name_suspend_resume_with_plugs,
        arg_sets=[(i, self.PlugInStage.BEFORE_SUSPEND)
                  for i in range(self._MAX_SUSPEND_TIME_EXPONENT)],
    )
    self.generate_tests(
        test_logic=self.suspend_resume_with_plug,
        name_func=self.generate_test_name_suspend_resume_with_plugs,
        arg_sets=[(i, self.PlugInStage.DURING_SUSPEND)
                  for i in range(self._MAX_SUSPEND_TIME_EXPONENT)],
    )
    self.generate_tests(
        test_logic=self.suspend_resume_with_plug,
        name_func=self.generate_test_name_suspend_resume_with_plugs,
        arg_sets=[(i, self.PlugInStage.AFTER_SUSPEND)
                  for i in range(self._MAX_SUSPEND_TIME_EXPONENT)],
    )

    # Generate tests for suspend and resume stress test.
    self.generate_tests(
        test_logic=self.suspend_resume_stress,
        name_func=self.generate_test_name_suspend_resume_stress,
        arg_sets=[(i, self.PlugInStage.BEFORE_SUSPEND)
                  for i in range(self._MAX_SUSPEND_TIME_EXPONENT)],
    )
    self.generate_tests(
        test_logic=self.suspend_resume_stress,
        name_func=self.generate_test_name_suspend_resume_stress,
        arg_sets=[(i, self.PlugInStage.DURING_SUSPEND)
                  for i in range(self._MAX_SUSPEND_TIME_EXPONENT)],
    )
    self.generate_tests(
        test_logic=self.suspend_resume_stress,
        name_func=self.generate_test_name_suspend_resume_stress,
        arg_sets=[(i, self.PlugInStage.AFTER_SUSPEND)
                  for i in range(self._MAX_SUSPEND_TIME_EXPONENT)],
    )

    # Generate tests for stress on plug.
    self.generate_tests(
        test_logic=self.stress_on_forever_plug,
        name_func=self.generate_test_name_stress_on_forever_plug,
        arg_sets=[(i,) for i in range(self._MAX_SUSPEND_TIME_EXPONENT)],
    )

  def setup_class(self):
    super().setup_class(require_servo=True)

  def generate_test_name_suspend_resume_with_plugs(self, exp: int,
                                                   stage: PlugInStage):
    """Generates the test name for suspend and resume with different stages of displays plugging."""
    prefix = "plug_then_" if stage == self.PlugInStage.BEFORE_SUSPEND else ""
    infix = "then_plug_" if stage == self.PlugInStage.DURING_SUSPEND else ""
    suffix = "_then_plug" if stage == self.PlugInStage.AFTER_SUSPEND else ""
    return (
        f"test_{prefix}suspend_for_{self._generate_suspend_time(exp)}_"
        f"{infix}then_resume{suffix}"
    )

  def generate_test_name_suspend_resume_stress(self, exp: int,
                                               stage: PlugInStage):
    """Generates the test name for suspend and resume stress test."""
    prefix = "plug_then_" if stage == self.PlugInStage.BEFORE_SUSPEND else ""
    infix = "then_plug_" if stage == self.PlugInStage.DURING_SUSPEND else ""
    suffix = "_then_plug" if stage == self.PlugInStage.AFTER_SUSPEND else ""
    return (
        f"test_{prefix}suspend_stress_for_{self._generate_suspend_time(exp)}_"
        f"{infix}then_resume{suffix}"
    )

  def generate_test_name_stress_on_forever_plug(self, exp: int):
    """Generates the test name for stress on plug test."""
    return f"test_stress_on_forever_plug_for_{self._generate_suspend_time(exp)}"

  def suspend_resume_with_plug(self, exp: int, stage: PlugInStage):
    """Tests the suspend and resume functionality.

    This test verifies that the device can suspend and resume correctly with
    variable suspend times, and that it can handle the plugging and unplugging
    of displays during different stages of the suspend/resume process.

    The test is parameterized by:
      - exp: An integer that determines the duration of the suspend period.
        The suspend time is calculated as {_SUSPEND_TIME_BASE} raised to the
        power of exp.
        This allows to test different suspend times in each test iteration.
      - stage: An enum that determines when the displays will be plugged.
        - BEFORE_SUSPEND: Displays are plugged before the device is suspended.
        - DURING_SUSPEND: Displays are plugged while the device is suspended.
        - AFTER_SUSPEND: Displays are plugged after the device is resumed.
        This allows to test different plug stages in each test iteration.

    The test performs the following steps:
      1.  If the stage is BEFORE_SUSPEND, it plugs new displays.
      2.  It suspends the device.
      3.  If the stage is DURING_SUSPEND, it plugs new displays.
      4.  It waits for a duration determined by the exp parameter.
      5.  It resumes the device.
      6.  If the stage is AFTER_SUSPEND, it plugs new displays.
      7.  It asserts that the device is online after resuming.

    This test is designed to test the suspend/resume functionality with
    different suspend times and plug stages in each test iteration.
    """
    if stage == self.PlugInStage.BEFORE_SUSPEND:
      self._ucd_manager.set_total_displays_count(self._PLUGGED_DISPLAYS)
      logging.debug("Plugging in external displays before suspend.")

    with dut_state_manager.EnterStateAndReturnToPowerOn(
        self.dut, dut_state_manager.PowerState.SUSPEND
    ):
      if stage == self.PlugInStage.DURING_SUSPEND:
        self._ucd_manager.set_total_displays_count(self._PLUGGED_DISPLAYS)
        logging.debug("Plugging in external displays during suspend.")
      logging.debug("Waiting for %f seconds before resuming.",
                    self._generate_suspend_time(exp))
      time.sleep(self._generate_suspend_time(exp))

    logging.debug("Resumed device.")
    if stage == self.PlugInStage.AFTER_SUSPEND:
      logging.debug("Plugging in external displays after resume.")
      self._ucd_manager.set_total_displays_count(self._PLUGGED_DISPLAYS)

    self._check_for_displays_on(self._PLUGGED_DISPLAYS,
                                self._generate_suspend_time(exp))

  def suspend_resume_stress(self, exp: int, stage: PlugInStage):
    """Tests the suspend and resume functionality with stress.

    This test repeats the suspend_resume_with_plug test multiple times
    to stress the suspend and resume functionality of the device.
    This helps to identify potential issues that may not be apparent
    in a single iteration of the test.

    The test is parameterized by:
      - exp: An integer that determines the duration of the suspend period.
      - stage: An enum that determines when the displays will be plugged.

    The test performs the following steps:
      1.  It repeats the suspend_resume_with_plug test for a number of times
          defined by _STESS_ITERATION_COUNT.
    """

    for _ in range(self._STESS_ITERATION_COUNT):
      self.suspend_resume_with_plug(exp, stage)

  def stress_on_forever_plug(self, exp):
    """Tests the stress on plug functionality.

    This test repeats the plug and unplug functionality multiple times
    to stress the display plug and unplug functionality of the device.
    This helps to identify potential issues that may not be apparent
    in a single iteration of the test.

    The test is parameterized by:
      - exp: An integer that determines the duration of the suspend period.

    The test performs the following steps:
      1.  It plugs the displays.
      2.  It repeats the suspend and resume for a number of times
          defined by _STESS_ITERATION_COUNT.
      3.  It asserts that the device is online and the displays are on.
    """
    self._ucd_manager.set_total_displays_count(self._PLUGGED_DISPLAYS)

    for _ in range(self._STESS_ITERATION_COUNT):
      with dut_state_manager.EnterStateAndReturnToPowerOn(
          self.dut, dut_state_manager.PowerState.SUSPEND
      ):
        time.sleep(self._generate_suspend_time(exp))

      self._check_for_displays_on(self._PLUGGED_DISPLAYS,
                                  self._generate_suspend_time(exp))

  def _generate_suspend_time(self, exp: int):
    """Generates the suspend time for the test."""
    return round(self._SUSPEND_TIME_BASE ** exp, 1)

  def _check_for_displays_on(self, display_count: int, suspend_time: float):
    asserts.assert_true(
        self._ucd_manager.are_displays_reporting_stream_info(display_count),
        f"External displays are not active for {display_count} displays.",
    )
    asserts.assert_true(
        self.dut.is_device_online(20),
        (
            "Device is not reporting online after suspending for "
            f"{suspend_time} seconds."
        ),
    )

    self.check_all_screenshots_for_displays(display_count)


class SuspendResumeTestSuite(base_suite.BaseSuite):
  """Test suite for testing the suspend and resume functionality."""

  def setup_suite(self, config: config_parser.TestRunConfig):
    self.add_test_class(SuspendResumeTest)


def main() -> None:
  suite_runner.run_suite_class()

if __name__ == "__main__":
  main()
