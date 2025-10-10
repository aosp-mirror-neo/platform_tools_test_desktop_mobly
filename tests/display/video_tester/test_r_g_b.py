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

import logging
import time

from display.utils import ucd_base_test
from lib.pasit import display_painter
from lib.pasit import pasit_display
from lib.utils import image
from mobly import base_suite
from mobly import config_parser
from mobly import suite_runner


class RGBTest(ucd_base_test.UcdBaseTest):
  """Test class for testing the system bandwidth with multiple displays.

  This class includes tests to verify the system's ability to handle an
  increasing and decreasing number of displays, ensuring that each display is
  correctly activated and managed.
  """

  display: pasit_display.PasitDisplay
  painter: display_painter.DisplayPainter
  internal_display_id: str
  _DISPLAY_STABILIZATION_TIME_SECONDS = 4

  def pre_run(self):
    for i in range(1, self._UCD_ABSOLUTE_MAX_CONNECTED_DISPLAYS + 1):
      self.generate_tests(
          test_logic=self.color_on_displays,
          name_func=self.generate_test_name_color_on_displays,
          arg_sets=[
              (color, i)
              for color in [
                  image.NamedColor.RED,
                  image.NamedColor.GREEN,
                  image.NamedColor.BLUE,
              ]
          ],
      )

  def setup_class(self):
    super().setup_class()
    self.painter = self.create(display_painter)
    self.internal_display_id = self.helper.get_internal_display_id()

  def teardown_test(self):
    self.painter.safe_clean_color_on_display()
    super().teardown_test()

  def generate_test_name_color_on_displays(
      self, color: image.NamedColor, display_count: int
  ):
    """Generate a test name for displaying a color on multiple displays."""
    return f"test_{color.name}_on_{display_count}_displays"

  def color_on_displays(self, color: image.NamedColor, display_count: int):
    """Display a color on all displays connected to the DUT."""
    self.skip_if_display_count_not_supported(display_count)

    self._ucd_manager.plug_additional_displays_to_active_displays(display_count)
    external_display_ids = self.helper.get_external_display_ids(
        self.internal_display_id, display_count
    )

    for display_id in external_display_ids:
      print(f"Showing color {color.value} on display {display_id}")
      logging.info("Showing color %s on display %s", color.value, display_id)
      self.painter.show_color_on_display(color.value, display_id)
      # Wait for the display to stabilize.
      time.sleep(self._DISPLAY_STABILIZATION_TIME_SECONDS)

    self.check_all_screenshots_for_displays(display_count, color.value)


class RGBTestSuite(base_suite.BaseSuite):
  """Test suite for testing displays with different colors."""

  def setup_suite(self, _: config_parser.TestRunConfig):
    self.add_test_class(RGBTest)


if __name__ == "__main__":
  suite_runner.run_suite_class()
