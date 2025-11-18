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

"""Testing the most basic operation of a DUT with UCD: Sanity Check."""

from display.utils import ucd_test_base
from mobly import base_suite
from mobly import config_parser
from mobly import suite_runner


class BasicTest(ucd_test_base.UcdTestBase):
  """Add a letter prefix to the test name to make them run in order."""

  def test_a_plug_single_display(self):
    """Tests the system's ability to plug in a single display."""

    self._ucd_manager.replug_displays(display_count=1, wait_for_active=True)

  def test_b_plug_and_unplug_display(self):
    """Tests the system's ability to plug in and unplug a display."""

    self._ucd_manager.replug_displays(display_count=1, wait_for_active=True)
    self._ucd_manager.unplug_all_displays(wait_for_active=True)

  def test_c_screenshot_single_display(self):
    """Tests the system's ability to take a screenshot of a single display."""

    self._ucd_manager.replug_displays(display_count=1, wait_for_active=True)
    self.check_all_screenshots_for_displays(1)


class BasicTestSuite(base_suite.BaseSuite):
  """Test suite for testing the most basic operations of a DUT with UCD."""

  def setup_suite(self, config: config_parser.TestRunConfig):
    self.add_test_class(BasicTest)


def main() -> None:
  suite_runner.run_suite_class()


if __name__ == "__main__":
  main()
