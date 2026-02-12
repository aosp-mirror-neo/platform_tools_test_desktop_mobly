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

"""Test that verifies HID detection and functionality."""

import logging

from lib.pasit import dut_state_manager
from lib.pasit import hid_keys
from lib.pasit import pasit_hid
from lib.utils import functools
from mobly import test_runner
from pasit.hid import hid_base_test


@functools.generate_tests
class PlugInHIDTest(hid_base_test.HIDBaseTest):
  """Test for HID detection and basic functionality across various power state transitions."""

  def setup_test(self):
    super().setup_test()
    self.unplug_hid_emulator()

  def teardown_test(self):
    self.hid.stop_key_capture()
    super().teardown_test()

  @functools.with_variants(
      on=(dut_state_manager.PowerState.ON,),
      off=(dut_state_manager.PowerState.OFF,),
      suspended=(dut_state_manager.PowerState.SUSPEND,),
  )
  def test_plug_in_hid_when_dut(
      self, target_state: dut_state_manager.PowerState
  ) -> None:
    """Scenario: Transition to state -> Plug in HID -> Return to ON.

    Args:
      target_state: Target DUT power state
    """

    with dut_state_manager.EnterStateAndReturnToPowerOn(self.dut, target_state):
      self.plug_in_hid_emulator()
    self.emulator.initialize()
    self.hid.start_key_capture()
    logging.info('Verifying Top Row keys')
    self.verify_all_keys_captured(
        self.emulator, [key for key in hid_keys.Function]
    )
    logging.info('Verifying Alphanumeric keys')
    self.verify_all_keys_captured(
        self.emulator, [key for key in hid_keys.Alphanumeric]
    )

  @functools.with_variants(
      shutdown=(dut_state_manager.PowerAction.SHUTDOWN,),
      suspend=(dut_state_manager.PowerAction.SUSPEND,),
      reboot=(dut_state_manager.PowerAction.REBOOT,),
  )
  def test_plug_in_hid_then(
      self, target_action: dut_state_manager.PowerAction
  ) -> None:
    """Scenario: Plug in HID while ON -> Transition -> Verify persistence.

    Args:
      target_action: Power Action to be performed on DUT
    """

    self.plug_in_hid_emulator()
    dut_state_manager.execute_power_action(self.dut, target_action)
    self.emulator.initialize()
    self.hid.start_key_capture()
    self.verify_all_keys_captured(self.emulator, [hid_keys.Alphanumeric.KEY_A])

  def test_keyboard_in_guest_mode(self) -> None:
    """Verifies top row and character keys in Guest Mode."""

    self.hid.cleanup()
    self.plug_in_hid_emulator()

    self.dut.user_tools.guest_mode()

    self.hid = self.create(pasit_hid)
    self.emulator.initialize()
    self.hid.start_key_capture()
    self.capture_screenshots('key_capture_started')

    logging.info('Verifying Top Row keys.')
    self.verify_all_keys_captured(
        self.emulator, [key for key in hid_keys.Function]
    )

    logging.info('Verifying Alphanumeric keys.')
    self.verify_all_keys_captured(
        self.emulator, [key for key in hid_keys.Alphanumeric]
    )


if __name__ == '__main__':
  test_runner.main()
