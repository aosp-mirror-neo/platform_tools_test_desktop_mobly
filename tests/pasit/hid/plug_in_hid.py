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

"""Test that verifies HID keyboard functionality across DUT power states."""

from lib.pasit import dut_state_manager
from lib.pasit import pasit_hid
from lib.utils import functools
from mobly import test_runner
from pasit.hid import hid_base_test


@functools.generate_tests
class PlugInHIDTest(hid_base_test.HIDBaseTest):
  """Verifies top row and character keys persist through power cycles."""

  def setup_class(self):
    super().setup_class()  # pylint: disable=attribute-error
    self.hid = self.create(pasit_hid)

  def teardown_test(self):
    self.hid.stop_key_capture()
    super().teardown_test()  # pylint: disable=attribute-error

  def teardown_class(self):
    if hasattr(self, 'hid'):
      self.hid.cleanup()
    super().teardown_class()  # pylint: disable=attribute-error

  @functools.with_variants(
      on=(dut_state_manager.PowerState.ON,),
      off=(dut_state_manager.PowerState.OFF,),
      suspended=(dut_state_manager.PowerState.SUSPEND,),
  )
  def test_plug_in_hid_when_dut(
      self, target_state: dut_state_manager.PowerState
  ):
    """Scenario: Verify keyboard functionality while in a static power state.

    Args:
      target_state: The PowerState to evaluate.
    """
    with dut_state_manager.EnterStateAndReturnToPowerOn(self.dut, target_state):
      self.plug_in_hid_emulator()

    self.emulator.initialize()
    self.validate_keyboard_input(self.hid)

  @functools.with_variants(
      shutdown=(dut_state_manager.PowerAction.SHUTDOWN,),
      suspend=(dut_state_manager.PowerAction.SUSPEND,),
      reboot=(dut_state_manager.PowerAction.REBOOT,),
  )
  def test_plug_in_hid_then(self, target_action: dut_state_manager.PowerAction):
    """Scenario: Verify keyboard functionality after a power action.

    Args:
      target_action: Power Action to be performed on DUT.
    """
    self.plug_in_hid_emulator()
    dut_state_manager.execute_power_action(self.dut, target_action)

    self.emulator.initialize()
    self.validate_keyboard_input(self.hid)


if __name__ == '__main__':
  test_runner.main()
