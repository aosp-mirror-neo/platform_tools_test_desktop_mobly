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

"""Test that plugs in an external display with lid closed when DUT is in different states."""

import logging

from android.platform.test.annotations import DesktopTest
from lib.pasit import dut_state_manager
from lib.pasit import pasit_display
from lib.pasit import peripheral_connector
from lib.pasit import test_policy
from lib.utils import functools
from lib.utils import image
from lib.utils import retry
from mobly import asserts
from mobly import test_runner
from pasit.display import display_base_test


@DesktopTest(
    cujs=[
        'b/476200925',  # External display(s) work when clamshell lid is shut
    ],
)
@functools.generate_tests
class DockedModeExternalDisplayTest(display_base_test.DisplayBaseTest):
  """Test that external displays remain active with lid closed when DUT is in different states."""

  def teardown_test(self):
    """Handle the teardown for the test."""
    self.dut.set_lid_open()
    super().teardown_test()  # pylint: disable=attribute-error

  @functools.with_dimensions(
      reboot=dut_state_manager.PowerAction.REBOOT,
      shutdown=dut_state_manager.PowerAction.SHUTDOWN,
      suspend=dut_state_manager.PowerAction.SUSPEND,
  )
  @functools.with_dimensions(
      dock_one_display=(peripheral_connector.ConnectionType.DOCK, 1),
      dockless_one_display=(peripheral_connector.ConnectionType.DOCKLESS, 1),
      dock_two_display=(peripheral_connector.ConnectionType.DOCK, 2),
      daisychain_two_display=(
          peripheral_connector.ConnectionType.DAISY_CHAIN,
          2,
      ),
  )
  def test_enter_docked_mode_then(
      self,
      power_action: dut_state_manager.PowerAction,
      connection_type: peripheral_connector.ConnectionType,
      external_display_count: int,
  ):
    """Test that external displays remain active with lid closed when DUT is in different states."""
    # TODO: b/489083801 - skip reboot with two dock display as DUT
    # does not come online after reboot.
    asserts.skip_if(
        power_action == dut_state_manager.PowerAction.REBOOT
        and connection_type == peripheral_connector.ConnectionType.DOCK
        and external_display_count > 1,
        'b/489083801 reboot with dock_two_display failing.',
    )
    self.skip_if_servo_needed_and_not_configured(power_action)
    internal_display_id = self.helper.get_internal_display_id()

    self.plug_in_external_displays(external_display_count, connection_type)

    self.verify_display_count(
        external_display_count + 1,
        'after external displays plug in',
    )

    display_id_to_camera_id = self.map_displays_to_cameras_with_retries()
    # pylint: disable=unused-variable
    external_display_ids = self.helper.get_external_display_ids(
        internal_display_id, external_display_count
    )

    self._close_lid()
    self.verify_display_count(
        external_display_count + 1,
        'after lid closed and before power action',
        # When lid is closed,  the internal display still detected, but it
        # should be turned off.
        expected_off=[internal_display_id],
    )
    self._verify_internal_display_is_blank(
        display_id_to_camera_id, internal_display_id
    )
    dut_state_manager.execute_power_action(self.dut, power_action)

    self.verify_display_count(
        external_display_count + 1,
        'after lid closed',
        expected_off=[internal_display_id],
    )

    # TODO(b/479143371): The display count remains the same, but display IDs
    # are swapped after the lid is closed. Inactive display IDs are still
    # being returned alongside active ones, causing the camera mapping
    # to become stale.
    # self._verify_external_display_colors_after_lid_closed(
    #     display_id_to_camera_id, external_display_ids
    # )

  @functools.with_variants(
      one_display_dock=(peripheral_connector.ConnectionType.DOCK, 1),
      one_display_dockless=(peripheral_connector.ConnectionType.DOCKLESS, 1),
      two_displays_dock=(peripheral_connector.ConnectionType.DOCK, 2),
      two_displays_daisychain=(
          peripheral_connector.ConnectionType.DAISY_CHAIN,
          2,
      ),
  )
  def test_enter_docked_mode_then_exit(
      self,
      connection_type: peripheral_connector.ConnectionType,
      external_display_count: int,
  ):
    """Tests display switching between internal and external screens.

    Verifies that content moves correctly when opening and closing the lid.

    Args:
      connection_type: Type of external display connections.
      external_display_count: Number of external displays connected.
    """

    internal_display_id = self.helper.get_internal_display_id()

    self.plug_in_external_displays(external_display_count, connection_type)
    self.verify_display_count(
        external_display_count + 1,
        'after external displays plug in',
    )

    display_id_to_camera_id = self.map_displays_to_cameras_with_retries()
    external_display_ids = self.helper.get_external_display_ids(
        internal_display_id, external_display_count
    )

    self.painter.show_color_on_display(
        image.NamedColor.RED.value, internal_display_id
    )

    self._close_lid()
    self.verify_display_count(
        external_display_count + 1,
        'after lid closed',
        expected_off=[internal_display_id],
    )
    self._verify_internal_display_is_blank(
        display_id_to_camera_id, internal_display_id
    )
    self._verify_red_moved_to_external_display(
        display_id_to_camera_id, external_display_ids
    )

    self._open_lid()

    self.verify_display_count(external_display_count + 1, 'after lid opened')
    self.verify_captured_color(
        display_id_to_camera_id[internal_display_id],
        image.NamedColor.RED,
        camera_capture_name='internal_display_after_open',
        failure_message=(
            'Internal display did not show red after the lid was opened.'
        ),
    )

  def _open_lid(self) -> None:
    """Opens the lid of the DUT to exit docked mode."""
    logging.info('Opening lid to exit docked mode.')
    self.dut.set_lid_open()

  def _close_lid(self) -> None:
    """Closes the lid of the DUT to enter docked mode."""
    logging.info('Closing lid to enter docked mode.')
    self.dut.set_lid_closed()

  def _verify_external_display_colors_after_lid_closed(
      self,
      display_id_to_camera_id: dict[pasit_display.PasitDisplay.DisplayId, str],
      external_display_ids: list[pasit_display.PasitDisplay.DisplayId],
  ):
    """Test that external display shows correct color after lid is closed."""

    colors = [
        image.NamedColor.RED,
        image.NamedColor.GREEN,
        image.NamedColor.BLUE,
    ]

    display_id_to_color = dict(zip(external_display_ids, colors))
    for display_id, color in display_id_to_color.items():
      self.painter.show_color_on_display(color.value, display_id)
      self.capture_screenshots(
          f'external_display_{display_id}_shows_{color.name}_after_lid_close'
      )

    for display_id, color in display_id_to_color.items():
      self.verify_captured_color(
          display_id_to_camera_id[display_id],
          color,
          f'{color}_on_external_{display_id}',
          f'External display {display_id} failed to show {color}.',
      )

  def _verify_internal_display_is_blank(
      self,
      display_id_to_camera_id: dict[pasit_display.PasitDisplay.DisplayId, str],
      internal_display_id: pasit_display.PasitDisplay.DisplayId,
  ) -> None:
    """Verify internal display is black after lid close."""
    logging.info('Verifying internal display is black after lid close.')
    camera = display_id_to_camera_id[internal_display_id]

    self.verify_captured_color(
        camera,
        image.NamedColor.BLACK,
        f'black_after_lid_closed_{camera}',
        'Internal display should be black after lid closed.',
    )

  def _verify_red_moved_to_external_display(
      self,
      display_id_to_camera_id: dict[pasit_display.PasitDisplay.DisplayId, str],
      external_display_ids: list[pasit_display.PasitDisplay.DisplayId],
  ) -> None:
    """Verify RED color moved to one of the external displays."""
    logging.info('Verifying RED moved to one of the external displays.')

    red_color_found = False

    # pylint: disable=cell-var-from-loop
    for display_id in external_display_ids:
      match_status = retry.retry(
          lambda: self.camera_mapper.try_match_color(
              display_id_to_camera_id[display_id],
              image.NamedColor.RED,
              'red_moved_to_external_display',
          ),
          until=lambda status: status,
          policy=test_policy.DisplayTestPolicy.MATCH_COLOR_RETRY_POLICY,
      )

      if match_status:
        red_color_found = True
        logging.info(
            'Camera %s detected color RED on external display %r',
            display_id_to_camera_id[display_id],
            display_id,
        )

        break
    # pylint: enable=cell-var-from-loop
    asserts.assert_true(
        red_color_found,
        'Red color not found on any external display after lid close.',
    )


if __name__ == '__main__':
  test_runner.main()
