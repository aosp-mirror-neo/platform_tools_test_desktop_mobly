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

"""PASIT Display Suite."""

from mobly import base_suite
from mobly import config_parser
from mobly import suite_runner
from pasit.display import plug_in_external_display
from pasit.display import shutdown_with_external_display
from pasit.display import plug_in_two_external_displays
from pasit.display import unplug_external_display
from pasit.display import change_external_display_resolution
from pasit.display import night_light


class PasitDisplaySuite(base_suite.BaseSuite):
  """PASIT Display Suite."""

  def setup_suite(self, config: config_parser.TestRunConfig):
    self.add_test_class(unplug_external_display.UnplugExternalDisplayTest)
    self.add_test_class(plug_in_external_display.PlugInExternalDisplayTest)
    self.add_test_class(
        shutdown_with_external_display.ShutdownWithExternalDisplayTest
    )
    self.add_test_class(
        plug_in_two_external_displays.PlugInTwoExternalDisplaysTest
    )
    self.add_test_class(
        change_external_display_resolution.ChangeDisplayResolutionTest
    )
    self.add_test_class(night_light.NightLightTest)


def main() -> None:
  suite_runner.run_suite_class()


if __name__ == '__main__':
  main()
