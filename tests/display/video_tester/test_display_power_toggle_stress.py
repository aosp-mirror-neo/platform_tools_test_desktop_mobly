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

"""Testing the display power toggle functionality (stress tests)."""

from mobly import base_suite
from mobly import config_parser
from mobly import suite_runner

from . import test_display_power_toggle


class DisplayPowerToggleStressTest(
    test_display_power_toggle.DisplayPowerToggleTest
):
  """Test class for testing the display power toggle functionality (stress)."""

  def __init__(self, configs: config_parser.TestRunConfig):
    super().__init__(configs, enable_stress_tests=True)


class DisplayPowerToggleStressTestSuite(base_suite.BaseSuite):
  """Test suite for testing the display power toggle functionality (stress)."""

  def setup_suite(self, config: config_parser.TestRunConfig):
    self.add_test_class(DisplayPowerToggleStressTest)


def main() -> None:
  suite_runner.run_suite_class()


if __name__ == '__main__':
  main()
