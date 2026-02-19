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

import contextlib
from typing import Generator

from lib.pasit import dut_state_manager
from lib.pasit.passport import passport_host
from mobly import base_suite
from mobly import config_parser
from mobly import suite_runner

from . import display_on_off_base


class SuspendResumeTest(display_on_off_base.DisplayOnOffBase):
  """Test class for testing the suspend and resume functionality.

  This class includes tests for suspending and resuming the device with
  different suspend times and different stages of display plugging.
  It also includes stress tests to verify the stability of the suspend/resume
  functionality.
  """

  def __init__(
      self,
      configs: config_parser.TestRunConfig,
      enable_stress_tests: bool = False,
  ):
    super().__init__(configs, enable_stress_tests=enable_stress_tests)

  def setup_class(self):
    super().setup_class(require_servo=True)

  @property
  def power_off_verb(self) -> str:
    return 'suspend'

  @property
  def power_on_verb(self) -> str:
    return 'resume'

  @contextlib.contextmanager
  def power_cycle_displays(self) -> Generator[None, None, None]:
    """A context manager to suspend and resume the device."""
    with dut_state_manager.EnterStateAndReturnToPowerOn(
        self.dut, dut_state_manager.PowerState.SUSPEND
    ):
      yield


class SuspendResumeTestSuite(base_suite.BaseSuite):
  """Test suite for testing the suspend and resume functionality."""

  def setup_suite(self, config: config_parser.TestRunConfig):
    passport_host.update_passport_host_config(config)

    self.add_test_class(SuspendResumeTest, config)


def main() -> None:
  suite_runner.run_suite_class()


if __name__ == '__main__':
  main()
