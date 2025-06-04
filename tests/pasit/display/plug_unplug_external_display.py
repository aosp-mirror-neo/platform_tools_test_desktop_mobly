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

"""Test that plugs and unplugs an external display."""

import logging

from mobly import test_runner
from pasit.display import display_base_test
from utils import image


class PlugUnplugExternalDisplayTest(display_base_test.DisplayBaseTest):
  """Test that plugs and unplugs an external display.

  Plug external monitro and find display IDs and map cameras to displays for the
  test.
  Once the external display is plugged in, the test will verify that the
  background color is visible on the external display. Then unplug the external
  display and verify that the background color is visible on the internal
  display.
  """

  def teardown_test(self):
    self.dut.clean_color_on_display()
    super().teardown_test()

  def test_plug_unplug_external_display(self):
    """Test that counts the number of displays on the DUT."""
    internal_display_id = self._get_internal_display_id()

    self._plug_in_external_display()
    self._verify_display_count(2, 'after external display plug in')
    external_display_id = self._get_external_display_id(internal_display_id)

    display_id_to_camera_id = self._map_displays_to_cameras()

    logging.info('Open red background on external display')
    self.dut.show_color_on_display(
        image.NamedColor.RED.value, external_display_id
    )

    logging.info('Verify background color on external display')
    self.dut.get_screenshots(self.log_path, 'external_display_red')
    self._verify_captured_color(
        display_id_to_camera_id[external_display_id],
        image.NamedColor.RED.value,
        'external_display_red',
        'External display should have red color.',
    )

    self._unplug_external_display()
    self._verify_display_count(1, 'after external display unplug')

    logging.info('Verify background color is now on internal display')
    self.dut.get_screenshots(self.log_path, 'internal_display_red')
    self._verify_captured_color(
        display_id_to_camera_id[internal_display_id],
        image.NamedColor.RED.value,
        'internal_display_red',
        'Internal display should have red color.',
    )


if __name__ == '__main__':
  test_runner.main()
