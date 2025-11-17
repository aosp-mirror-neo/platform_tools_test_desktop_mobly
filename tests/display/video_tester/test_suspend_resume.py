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

  # TODO: b/391360720 - When we gain more confidence in our max display support,
  # replace this by self.max_tested_displays
  _MAX_DISPLAYS_TO_TEST = 2
  _SUSPEND_TIME_BASE = 3.7
  _MAX_SUSPEND_TIME_EXPONENT = 4
  _STRESS_ITERATION_COUNT = 77

  class PlugInStage(enum.Enum):
    """Enum for the different phases of the suspend/resume test."""

    BEFORE_SUSPEND = 1
    DURING_SUSPEND = 2
    AFTER_SUSPEND = 3

  def pre_run(self):
    for display_count in range(1, self._MAX_DISPLAYS_TO_TEST + 1):

      for stage in self.PlugInStage:
        self.generate_tests(
            test_logic=self.suspend_resume_with_plug,
            name_func=self.generate_test_name_suspend_resume_with_plugs,
            arg_sets=[
                (i + 1, stage, display_count)
                for i in range(self._MAX_SUSPEND_TIME_EXPONENT)
            ],
        )

      for stage in self.PlugInStage:
        self.generate_tests(
            test_logic=self.suspend_resume_with_plug_stress,
            name_func=self.generate_test_name_suspend_resume_with_plugs_stress,
            arg_sets=[
                (i + 1, stage, display_count)
                for i in range(self._MAX_SUSPEND_TIME_EXPONENT)
            ],
        )

      self.generate_tests(
          test_logic=self.suspend_resume_n_times_while_plugged,
          name_func=self.generate_test_name_suspend_resume_n_times_while_plugged,
          arg_sets=[
              (i + 1, display_count)
              for i in range(self._MAX_SUSPEND_TIME_EXPONENT)
          ],
      )

      self.generate_tests(
          test_logic=self.suspend_resume_with_unplug_during_suspend,
          name_func=self.generate_test_name_suspend_resume_with_unplug_during_suspend,
          arg_sets=[
              (i + 1, display_count)
              for i in range(self._MAX_SUSPEND_TIME_EXPONENT)
          ],
      )

      self.generate_tests(
          test_logic=self.suspend_resume_in_mirror_mode,
          name_func=self.generate_test_name_suspend_resume_in_mirror_mode,
          arg_sets=[(display_count,)],
      )

      self.generate_tests(
          test_logic=self.suspend_resume_in_clamshell_mode,
          name_func=self.generate_test_name_suspend_resume_in_clamshell_mode,
          arg_sets=[(display_count,)],
      )

  def setup_class(self):
    super().setup_class(require_servo=True)

  def teardown_test(self):
    self.display.set_mirror_mode(False)
    self.dut.set_lid_open()
    super().teardown_test()

  def generate_test_name_suspend_resume_with_plugs(
      self, exp: int, stage: PlugInStage, display_count: int
  ):
    """Generates the test name for suspend and resume with different stages of displays plugging."""
    suspend_time = self._generate_suspend_time(exp)
    display_str = f"{display_count}_display{'s' if display_count > 1 else ''}"
    match stage:
      case self.PlugInStage.BEFORE_SUSPEND:
        return (
            f'test_plug_{display_str}_then_suspend_{suspend_time}s_then_resume'
        )
      case self.PlugInStage.DURING_SUSPEND:
        return (
            f'test_suspend_{suspend_time}s_then_plug_{display_str}_then_resume'
        )
      case self.PlugInStage.AFTER_SUSPEND:
        return (
            f'test_suspend_{suspend_time}s_then_resume_then_plug_{display_str}'
        )
      case _:
        raise ValueError(f'Unsupported stage: {stage}')

  def generate_test_name_suspend_resume_with_plugs_stress(
      self, exp: int, stage: PlugInStage, display_count: int
  ):
    """Generates the test name for suspend and resume with different stages of displays plugging, repeated multiple times."""
    test_name = self.generate_test_name_suspend_resume_with_plugs(
        exp, stage, display_count
    )
    return f'{test_name}_{self._STRESS_ITERATION_COUNT}_times'

  def generate_test_name_suspend_resume_n_times_while_plugged(
      self, exp: int, display_count: int
  ):
    """Generates the test name for suspend/resume with displays constantly connected, repeated multiple times."""
    suspend_time = self._generate_suspend_time(exp)
    display_str = f"{display_count}_display{'s' if display_count > 1 else ''}"
    return (
        f'test_suspend_{suspend_time}s_resume_{self._STRESS_ITERATION_COUNT}_times_with_'
        f'{display_str}_plugged'
    )

  def generate_test_name_suspend_resume_with_unplug_during_suspend(
      self, exp: int, display_count: int
  ):
    """Generates the test name for suspend/resume with displays unplugging during suspend."""
    suspend_time = self._generate_suspend_time(exp)
    display_str = f"{display_count}_display{'s' if display_count > 1 else ''}"
    return f'test_plug_{display_str}_then_suspend_{suspend_time}s_then_unplug_then_resume'

  def generate_test_name_suspend_resume_in_mirror_mode(
      self, display_count: int
  ):
    """Generates the test name for suspend/resume in mirror mode."""
    display_str = f"{display_count}_display{'s' if display_count > 1 else ''}"
    return f'test_suspend_resume_in_mirror_mode_with_{display_str}'

  def generate_test_name_suspend_resume_in_clamshell_mode(
      self, display_count: int
  ):
    """Generates the test name for suspend/resume in clamshell mode."""
    display_str = f"{display_count}_display{'s' if display_count > 1 else ''}"
    return f'test_suspend_resume_in_clamshell_mode_with_{display_str}'

  def suspend_resume_with_plug(
      self, exp: int, stage: PlugInStage, display_count: int
  ):
    """Tests suspend and resume with displays plugged at various stages."""
    suspend_time = self._generate_suspend_time(exp)
    if stage == self.PlugInStage.BEFORE_SUSPEND:
      self._ucd_manager.set_total_displays_count(display_count)

    with dut_state_manager.EnterStateAndReturnToPowerOn(
        self.dut, dut_state_manager.PowerState.SUSPEND
    ):
      if stage == self.PlugInStage.DURING_SUSPEND:
        self._ucd_manager.set_total_displays_count(display_count)
        logging.debug('Plugging in external displays during suspend.')
      time.sleep(suspend_time)

    if stage == self.PlugInStage.AFTER_SUSPEND:
      self._ucd_manager.set_total_displays_count(display_count)

    self._check_for_displays_on(display_count, suspend_time)

  def suspend_resume_with_plug_stress(
      self, exp: int, stage: PlugInStage, display_count: int
  ):
    """Stress tests suspend and resume by repeating the test multiple times."""
    for i in range(self._STRESS_ITERATION_COUNT):
      logging.debug(
          'Stress test iteration %d/%d.', i + 1, self._STRESS_ITERATION_COUNT
      )
      self.suspend_resume_with_plug(exp, stage, display_count)
      self._ucd_manager.unplug_and_destroy_all_displays()

  def suspend_resume_n_times_while_plugged(self, exp: int, display_count: int):
    """Stress tests suspend/resume with displays constantly connected."""
    suspend_time = self._generate_suspend_time(exp)
    self._ucd_manager.set_total_displays_count(display_count)

    for i in range(self._STRESS_ITERATION_COUNT):
      logging.debug(
          'Iteration %d/%d: Suspending device.',
          i + 1,
          self._STRESS_ITERATION_COUNT,
      )
      with dut_state_manager.EnterStateAndReturnToPowerOn(
          self.dut, dut_state_manager.PowerState.SUSPEND
      ):
        time.sleep(suspend_time)
      logging.debug(
          'Iteration %d/%d: Resumed device.',
          i + 1,
          self._STRESS_ITERATION_COUNT,
      )

      self._check_for_displays_on(display_count, suspend_time)

  def suspend_resume_with_unplug_during_suspend(
      self, exp: int, display_count: int
  ):
    """Tests unplugging displays during suspend."""

    self._plug_in_and_verify_displays(display_count)

    with dut_state_manager.EnterStateAndReturnToPowerOn(
        self.dut, dut_state_manager.PowerState.SUSPEND
    ):
      logging.info('Unplugging displays during suspend.')
      self._ucd_manager.unplug_and_destroy_all_displays()
      suspend_time = self._generate_suspend_time(exp)
      time.sleep(suspend_time)

    logging.info('Resumed device. Verifying displays are off.')
    asserts.assert_true(
        self._ucd_manager.are_displays_reporting_stream_info(0),
        'Displays should be inactive after unplugging during suspend.',
    )

    self._plug_in_and_verify_displays(display_count)

  def suspend_resume_in_mirror_mode(self, display_count: int):
    """Tests suspend and resume with displays in mirror mode."""
    self._plug_in_and_verify_displays(display_count)

    logging.info('Enabling mirror mode.')
    self.display.set_mirror_mode(True)
    time.sleep(5)  # Give time for the mode to switch

    logging.info('Suspending device in mirror mode.')
    with dut_state_manager.EnterStateAndReturnToPowerOn(
        self.dut, dut_state_manager.PowerState.SUSPEND
    ):
      time.sleep(10)

    logging.info(
        'Resumed device. Verifying displays are active in mirror mode.'
    )
    self._check_for_displays_on(display_count, 0)
    asserts.assert_true(
        self.display.get_mirror_mode(), 'Device did not resume in mirror mode.'
    )

  def suspend_resume_in_clamshell_mode(self, display_count: int):
    """Tests suspend and resume with the DUT in clamshell mode."""

    self._plug_in_and_verify_displays(display_count)

    logging.info('Entering clamshell mode (closing lid).')
    self.dut.set_lid_closed()
    time.sleep(5)

    self._check_for_displays_on(display_count, 0)

    logging.info('Suspending device in clamshell mode.')
    with dut_state_manager.EnterStateAndReturnToPowerOn(
        self.dut, dut_state_manager.PowerState.SUSPEND
    ):
      time.sleep(10)

    logging.info(
        'Resumed device. Verifying external displays are still active.'
    )
    self._check_for_displays_on(display_count, 0)

  def _generate_suspend_time(self, exp: int):
    """Generates the suspend time for the test."""
    return round(self._SUSPEND_TIME_BASE**exp, 1)

  def _plug_in_and_verify_displays(self, display_count: int):
    self._ucd_manager.plug_additional_displays_to_active_displays(display_count)
    self._check_for_displays_on(display_count, 0)

  def _check_for_displays_on(self, display_count: int, suspend_time: float):
    logging.info('Verifying %d displays are on.', display_count)
    asserts.assert_true(
        self._ucd_manager.are_displays_reporting_stream_info(display_count),
        f'External displays are not active for {display_count} displays.',
    )
    asserts.assert_true(
        self.dut.is_device_online(),
        (
            'Device is not reporting online after suspending for '
            f'{suspend_time} seconds.'
        ),
    )

    logging.info('Verifying screenshots for all %d displays.', display_count)
    self.check_all_screenshots_for_displays(display_count)


class SuspendResumeTestSuite(base_suite.BaseSuite):
  """Test suite for testing the suspend and resume functionality."""

  def setup_suite(self, config: config_parser.TestRunConfig):
    self.add_test_class(SuspendResumeTest)


def main() -> None:
  suite_runner.run_suite_class()

if __name__ == '__main__':
  main()
