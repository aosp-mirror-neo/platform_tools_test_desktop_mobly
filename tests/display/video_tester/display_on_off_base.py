# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Base class for testing display on/off functionality."""

import abc
import enum
import logging
import time
from typing import Generator

from display.utils import ucd_test_base
from mobly import asserts
from mobly import config_parser


class DisplayOnOffBase(ucd_test_base.UcdTestBase, metaclass=abc.ABCMeta):
  """Base class for testing display on/off functionality.

  This class includes tests for turning displays off and on with
  different off times and different stages of display plugging.
  It also includes stress tests to verify the stability of the on/off
  functionality.
  """

  # TODO: b/391360720 - When we gain more confidence in our max display support,
  # replace this by self.max_tested_displays
  _MAX_DISPLAYS_TO_TEST = 2
  _SUSPEND_TIME_BASE = 3.7
  _MAX_OFF_TIME_EXPONENT = 4
  _STRESS_ITERATION_COUNT = 77

  def __init__(
      self,
      configs: config_parser.TestRunConfig,
      enable_stress_tests: bool = False,
  ):
    super().__init__(configs)
    self._enable_stress_tests = enable_stress_tests

  class PlugInStage(enum.Enum):
    """Enum for the different phases of the display on/off test."""

    BEFORE_POWER_OFF = 1
    DURING_POWER_OFF = 2
    AFTER_POWER_ON = 3

  @abc.abstractmethod
  def power_cycle_displays(self) -> Generator[None, None, None]:
    """A context manager to turn displays off and on."""
    raise NotImplementedError

  @property
  @abc.abstractmethod
  def power_off_verb(self) -> str:
    """The verb to use for the power off action in test names."""
    raise NotImplementedError

  @property
  @abc.abstractmethod
  def power_on_verb(self) -> str:
    """The verb to use for the power on action in test names."""
    raise NotImplementedError

  def pre_run(self):
    for display_count in range(1, self._MAX_DISPLAYS_TO_TEST + 1):
      if not self._enable_stress_tests:
        for stage in self.PlugInStage:
          self.generate_tests(
              test_logic=self._display_on_off_with_plug,
              name_func=self.generate_test_name_display_on_off_with_plugs,
              arg_sets=[
                  (i + 1, stage, display_count)
                  for i in range(self._MAX_OFF_TIME_EXPONENT)
              ],
          )

        self.generate_tests(
            test_logic=self._display_on_off_with_unplug_during_power_off,
            name_func=self.generate_test_name_display_on_off_with_unplug_during_power_off,
            arg_sets=[
                (i + 1, display_count)
                for i in range(self._MAX_OFF_TIME_EXPONENT)
            ],
        )

      # Stress tests
      else:
        for stage in self.PlugInStage:
          self.generate_tests(
              test_logic=self._display_on_off_with_plug_stress,
              name_func=self.generate_test_name_display_on_off_with_plugs_stress,
              arg_sets=[
                  (i + 1, stage, display_count)
                  for i in range(self._MAX_OFF_TIME_EXPONENT)
              ],
          )

        self.generate_tests(
            test_logic=self._display_on_off_n_times_while_plugged,
            name_func=self.generate_test_name_display_on_off_n_times_while_plugged,
            arg_sets=[
                (i + 1, display_count)
                for i in range(self._MAX_OFF_TIME_EXPONENT)
            ],
        )

  def generate_test_name_display_on_off_with_plugs(
      self, exp: int, stage: PlugInStage, display_count: int
  ):
    """Generates the test name for display on/off with different stages of displays plugging."""
    off_time = self._generate_off_time(exp)
    display_str = f"{display_count}_display{'s' if display_count > 1 else ''}"
    match stage:
      case self.PlugInStage.BEFORE_POWER_OFF:
        return f'test_plug_{display_str}_then_{self.power_off_verb}_{off_time}s_then_{self.power_on_verb}'
      case self.PlugInStage.DURING_POWER_OFF:
        return f'test_{self.power_off_verb}_{off_time}s_then_plug_{display_str}_then_{self.power_on_verb}'
      case self.PlugInStage.AFTER_POWER_ON:
        return f'test_{self.power_off_verb}_{off_time}s_then_{self.power_on_verb}_then_plug_{display_str}'
      case _:
        raise ValueError(f'Unsupported stage: {stage}')

  def generate_test_name_display_on_off_with_plugs_stress(
      self, exp: int, stage: PlugInStage, display_count: int
  ):
    """Generates the test name for display on/off with different stages of displays plugging, repeated multiple times."""
    test_name = self.generate_test_name_display_on_off_with_plugs(
        exp, stage, display_count
    )
    return f'{test_name}_{self._STRESS_ITERATION_COUNT}_times'

  def generate_test_name_display_on_off_n_times_while_plugged(
      self, exp: int, display_count: int
  ):
    """Generates the test name for display on/off with displays constantly connected, repeated multiple times."""
    off_time = self._generate_off_time(exp)
    display_str = f"{display_count}_display{'s' if display_count > 1 else ''}"
    return (
        f'test_{self.power_off_verb}_{off_time}s_{self.power_on_verb}_{self._STRESS_ITERATION_COUNT}_times_with_'
        f'{display_str}_plugged'
    )

  def generate_test_name_display_on_off_with_unplug_during_power_off(
      self, exp: int, display_count: int
  ):
    """Generates the test name for display on/off with displays unplugging during power off."""
    off_time = self._generate_off_time(exp)
    display_str = f"{display_count}_display{'s' if display_count > 1 else ''}"
    return f'test_plug_{display_str}_then_{self.power_off_verb}_{off_time}s_then_unplug_then_{self.power_on_verb}'

  def _display_on_off_with_plug(
      self, exp: int, stage: PlugInStage, display_count: int
  ):
    """Tests display on/off with displays plugged at various stages."""
    off_time = self._generate_off_time(exp)
    if stage == self.PlugInStage.BEFORE_POWER_OFF:
      self._ucd_manager.replug_displays(
          display_count=display_count, wait_for_active=False
      )

    with self.power_cycle_displays():
      if stage == self.PlugInStage.DURING_POWER_OFF:
        self._ucd_manager.replug_displays(
            display_count=display_count, wait_for_active=False
        )
        logging.debug('Plugging in external displays during power off.')
      time.sleep(off_time)

    if stage == self.PlugInStage.AFTER_POWER_ON:
      self._ucd_manager.replug_displays(
          display_count=display_count, wait_for_active=True
      )

    self._check_for_displays_on(display_count, off_time)

  def _display_on_off_with_plug_stress(
      self, exp: int, stage: PlugInStage, display_count: int
  ):
    """Stress tests display on/off by repeating the test multiple times."""
    for i in range(self._STRESS_ITERATION_COUNT):
      logging.debug(
          'Stress test iteration %d/%d.', i + 1, self._STRESS_ITERATION_COUNT
      )
      self._display_on_off_with_plug(exp, stage, display_count)
      self._ucd_manager.unplug_all_displays(wait_for_active=False)

  def _display_on_off_n_times_while_plugged(self, exp: int, display_count: int):
    """Stress tests display on/off with displays constantly connected."""
    off_time = self._generate_off_time(exp)
    self._ucd_manager.replug_displays(
        display_count=display_count, wait_for_active=False
    )

    for i in range(self._STRESS_ITERATION_COUNT):
      logging.debug(
          'Iteration %d/%d: Turning off displays.',
          i + 1,
          self._STRESS_ITERATION_COUNT,
      )
      with self.power_cycle_displays():
        time.sleep(off_time)
      logging.debug(
          'Iteration %d/%d: Turned on displays.',
          i + 1,
          self._STRESS_ITERATION_COUNT,
      )

      self._check_for_displays_on(display_count, off_time)

  def _display_on_off_with_unplug_during_power_off(
      self, exp: int, display_count: int
  ):
    """Tests unplugging displays during display power off."""
    self._plug_in_and_verify_displays(display_count)

    off_time = self._generate_off_time(exp)
    with self.power_cycle_displays():
      logging.info('Unplugging displays during power off.')
      self._ucd_manager.unplug_all_displays(wait_for_active=False)
      time.sleep(off_time)

    logging.info('Displays powered on. Verifying displays are off.')
    asserts.assert_true(
        self._ucd_manager.wait_for_display_count(0),
        'Displays should be inactive after unplugging during power off.',
    )

    self._plug_in_and_verify_displays(display_count)

  def _generate_off_time(self, exp: int) -> float:
    """Generates the off time for the test."""
    return round(self._MAX_OFF_TIME_EXPONENT**exp, 1)

  def _plug_in_and_verify_displays(self, display_count: int):
    self._ucd_manager.replug_displays(
        display_count=display_count, wait_for_active=True
    )
    self._check_for_displays_on(display_count, 0)

  def _check_for_displays_on(self, display_count: int, off_time: float):
    logging.info('Verifying %d displays are on.', display_count)
    asserts.assert_true(
        self._ucd_manager.wait_for_display_count(display_count),
        f'Expected {display_count} displays to be active.',
    )
    asserts.assert_true(
        self.dut.is_device_online(),
        (
            'Device is not reporting online after being off for '
            f'{off_time} seconds.'
        ),
    )

    logging.info('Verifying screenshots for all %d displays.', display_count)
    self.check_all_screenshots_for_displays(display_count)
