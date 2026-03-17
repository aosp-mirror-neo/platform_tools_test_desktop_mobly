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

"""Test that plugs in an external display when DUT is in different states."""

import logging

from android.platform.test.annotations import DesktopTest
from lib.pasit import dut_state_manager
from lib.pasit import peripheral_connector
from lib.utils import functools
from lib.utils import image
from mobly import test_runner
from pasit.display import display_base_test


# CUJs this test covers (full or partial) go/al-traceability
@DesktopTest(
    cujs=[
        'b/471032860',  # Dock and peripherals work after reboot/suspend
    ],
    manual=[
        'al_connect_disconnect_scenarios.boot_al_device_with_new_display_connected',
        'al_dock_and_display.connect_dp_display_with_usb_c_adapter',
        'al_dock_and_display.single_external_display_extended_mode',
        'al_dock_and_display.usb_typec_docking_station_testing',
    ],
)
@functools.generate_tests
class PlugInExternalDisplayTest(display_base_test.DisplayBaseTest):
  """Test that plugs in an external display when DUT is in different states."""

  @functools.with_dimensions(
      on=(dut_state_manager.PowerState.ON,),
      off=(dut_state_manager.PowerState.OFF,),
      suspended=(dut_state_manager.PowerState.SUSPEND,),
  )
  @functools.with_dimensions(
      dock=(peripheral_connector.ConnectionType.DOCK,),
      dockless=(peripheral_connector.ConnectionType.DOCKLESS,),
  )
  def test_plug_in_display_when_dut(
      self,
      state_when_plug_display: dut_state_manager.PowerState,
      connection_type: peripheral_connector.ConnectionType,
  ):
    """Test that plugs in an external display when DUT is in different states."""
    self.skip_if_servo_needed_and_not_configured(state_when_plug_display)

    with dut_state_manager.EnterStateAndReturnToPowerOn(
        self.dut, state_when_plug_display
    ):
      self.plug_in_external_display(connection_type)

    self.verify_display_count(2, 'after external display plug in')

    display_id_to_camera_id = self.map_displays_to_cameras_with_retries()

    logging.info('Open red background on external display')
    external_display_ids = self.helper.get_external_display_ids(1)
    external_display_id = external_display_ids[0]
    self.painter.show_color_on_display(
        image.NamedColor.RED.value, external_display_id
    )

    logging.info('Verify background color on external display')
    self.capture_screenshots('external_display_red')
    self.verify_captured_color(
        display_id_to_camera_id[external_display_id],
        image.NamedColor.RED,
        'external_display_red',
        'External display should have red color.',
    )


if __name__ == '__main__':
  test_runner.main()
