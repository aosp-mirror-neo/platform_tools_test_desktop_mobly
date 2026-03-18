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

"""Testing DSC with various configurations."""

from display.utils import ucd_test_base
from lib.pasit.passport import passport_host
from mobly import base_suite
from mobly import config_parser
from mobly import suite_runner


class DscTest(ucd_test_base.UcdTestBase):
  """Test class for testing DSC features."""

  def pre_run(self):
    arg_sets = []
    for dsc_enabled in [True, False]:
      for display_count in [1, 2]:
        arg_sets.append((dsc_enabled, display_count))

    self.generate_tests(
        test_logic=self.plug_with_dsc,
        name_func=self.generate_test_name_plug_with_dsc,
        arg_sets=arg_sets,
    )

  def generate_test_name_plug_with_dsc(
      self,
      enable_dsc: bool,
      display_count: int,
  ) -> str:
    """Generates the test name."""
    return f"test_dsc_{enable_dsc}_with_{display_count}_displays"

  def plug_with_dsc(
      self,
      enable_dsc: bool,
      display_count: int,
  ):
    """Tests the system's ability to plug in displays with DSC configuration."""
    self.skip_if_display_count_not_supported(display_count)

    self._ucd_manager.set_dp_video_spec(
        video_spec=self._original_dp_video_spec, dsc=enable_dsc
    )

    force_mst = display_count > 1

    self._ucd_manager.replug_displays(
        display_count=display_count, wait_for_active=True, force_mst=force_mst
    )
    self.check_all_screenshots_for_displays(display_count)


class DscTestSuite(base_suite.BaseSuite):
  """Test suite for testing DSC."""

  def setup_suite(self, config: config_parser.TestRunConfig):
    passport_host.update_passport_host_config(config)

    self.add_test_class(DscTest, config)


if __name__ == "__main__":
  suite_runner.run_suite_class()
