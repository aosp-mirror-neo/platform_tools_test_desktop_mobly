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

"""Test that plugs in two external displays when DUT is in different states."""

import logging
import itertools

from lib.utils import functools
from lib.pasit import dut_state_manager
from lib.utils import image
from mobly import asserts
from mobly import test_runner
from pasit.display import display_base_test

_EXTERNAL_DISPLAY_COUNT_AFTER_PLUG_IN = 2



# TODO: b/443128286 - Review if we need to merge this test class with
#plug_in_external_display.py.
@functools.generate_tests
class PlugInTwoExternalDisplaysTest(display_base_test.DisplayBaseTest):
  """Test that plugs in two external displays when DUT is in different states."""

  @functools.with_variants(
      on_dock=(
          dut_state_manager.PowerState.ON,
          display_base_test.DisplayPaths.DOCK,
      ),
      on_daisychain=(
          dut_state_manager.PowerState.ON,
          display_base_test.DisplayPaths.DAISY_CHAIN,
      ),
      off_dock=(
          dut_state_manager.PowerState.OFF,
          display_base_test.DisplayPaths.DOCK,
      ),
      off_daisychain=(
          dut_state_manager.PowerState.OFF,
          display_base_test.DisplayPaths.DAISY_CHAIN,
      ),
      suspended_dock=(
          dut_state_manager.PowerState.SUSPEND,
          display_base_test.DisplayPaths.DOCK,
      ),
      suspended_daisychain=(
          dut_state_manager.PowerState.SUSPEND,
          display_base_test.DisplayPaths.DAISY_CHAIN,
      ),
  )
  def test_plug_in_two_displays_when_dut(
      self,
      state_when_plug_display: dut_state_manager.PowerState,
      display_path: display_base_test.DisplayPaths,
  ):
    """Test that plugs in two external displays when DUT is in different states."""
    self._skip_if_servo_needed_and_not_configured(state_when_plug_display)
    self.setup_display_path(display_path)

    internal_display_id = self.helper.get_internal_display_id()
    with dut_state_manager.EnterStateAndReturnToPowerOn(
        self.dut, state_when_plug_display
    ):
      monitor_ids = self._get_monitor_device_ids()
      asserts.skip_if(
          len(monitor_ids) != _EXTERNAL_DISPLAY_COUNT_AFTER_PLUG_IN,
          f'Expected {_EXTERNAL_DISPLAY_COUNT_AFTER_PLUG_IN} monitors, but'
          f' found {len(monitor_ids)}.',
      )
      for monitor_id in monitor_ids:
        self._plug_in_external_display(monitor_id)

    self._verify_display_count(
        _EXTERNAL_DISPLAY_COUNT_AFTER_PLUG_IN + 1,
        'after two external displays plug in')

    display_id_to_camera_id = self._map_displays_to_cameras_with_retries()

    external_display_ids = self.helper.get_external_display_ids(
        internal_display_id, _EXTERNAL_DISPLAY_COUNT_AFTER_PLUG_IN
    )

    for i, external_display_id in enumerate(external_display_ids):
      logging.info(
          'Open red background on external display %d', i
      )
      self.painter.show_color_on_display(
          image.NamedColor.RED.value, external_display_id
      )

      logging.info('Verify background color on external display %d', i)
      self._capture_screenshots(f'external_display_{i}_red')
      self._verify_captured_color(
          display_id_to_camera_id[external_display_id],
          image.NamedColor.RED,
          f'external_display_{i}_red',
          f'External display {i} should have red color.',
      )


if __name__ == '__main__':
  test_runner.main()
