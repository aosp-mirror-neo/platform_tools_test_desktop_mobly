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

"""Test that unplugs an external display when DUT is in different states."""

import logging

from lib.pasit import dut_state_manager
from lib.utils import image
from mobly import test_runner
from pasit.display import display_base_test


# Each tuple is a list of arguments for a test case. The first argument is a
# PowerState indicating the DUT state when external display is unplugged.
_TEST_ARGUMENTS: tuple[tuple[dut_state_manager.PowerState, ...], ...] = (
    (dut_state_manager.PowerState.ON,),
    (dut_state_manager.PowerState.SUSPEND,),
)


class UnplugExternalDisplayTest(display_base_test.DisplayBaseTest):
  """Test that unplugs an external display when DUT is in different states."""

  def pre_run(self):
    """Generate tests for each test case."""
    self.generate_tests(
        test_logic=self.display_test_logic,
        name_func=self.display_test_name,
        arg_sets=_TEST_ARGUMENTS,
    )

  def display_test_name(
      self, state_when_unplug_display: dut_state_manager.PowerState
  ) -> str:
    """Get the test name for the given test args."""
    return f'test_unplug_display_when_dut_{state_when_unplug_display.value}'

  def display_test_logic(
      self, state_when_unplug_display: dut_state_manager.PowerState
  ):
    """Test that unplugs an external display when DUT is in different states."""
    self._skip_if_servo_needed_and_not_configured(state_when_unplug_display)

    internal_display_id = self.helper.get_internal_display_id()

    self._plug_in_external_display()
    self._verify_display_count(2, 'after external display plug in')

    display_id_to_camera_id = self._map_displays_to_cameras_with_retries()

    logging.info('Open red background on external display')
    external_display_ids = self.helper.get_external_display_ids(
        internal_display_id, 1
    )
    external_display_id = external_display_ids[0]

    self.painter.show_color_on_display(
        image.NamedColor.RED.value, external_display_id
    )

    logging.info('Verify background color on external display')
    self._capture_screenshots('external_display_red')
    self._verify_captured_color(
        display_id_to_camera_id[external_display_id],
        image.NamedColor.RED,
        'external_display_red',
        'Red background was not detected on the external display.',
    )

    with dut_state_manager.EnterStateAndReturnToPowerOn(
        self.dut, state_when_unplug_display
    ):
      self._unplug_external_display()
    self._verify_display_count(1, 'after external display unplug')

    # Verify the background color window switching between external and internal
    # display.
    logging.info('Verify background color is now on internal display')
    self._capture_screenshots('internal_display_red')
    self._verify_captured_color(
        display_id_to_camera_id[internal_display_id],
        image.NamedColor.RED,
        'internal_display_red',
        'Red background did not move to the internal display after the'
        ' external display was unplugged.',
    )
    # Replug the external display and verify the color moves back.
    logging.info('Replugging external display.')
    self._plug_in_external_display()
    self._verify_display_count(2, 'after external display replug')
    logging.info('Verify background color is now back on external display')
    self._capture_screenshots('external_display_red_after_replug')
    self._verify_captured_color(
        display_id_to_camera_id[external_display_id],
        image.NamedColor.RED,
        'external_display_red_after_replug',
        'Red background did not move back to the external display after it was'
        ' plugged back in.',
    )


if __name__ == '__main__':
  test_runner.main()
