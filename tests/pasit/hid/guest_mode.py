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

from android.platform.test.annotations import DesktopTest
from lib.pasit import hid_keys
from lib.pasit import pasit_hid
from mobly import test_runner
from pasit.hid import hid_base_test


@DesktopTest(
    cujs=[
        'b/471032970',  # Keyboard/mouse work in guest mode
    ],
)
class GuestModeTest(hid_base_test.HIDBaseTest):
  """Test for HID detection and basic functionality in Guest Mode."""

  def setup_test(self):
    """Plugs in the HID emulator and initializes it.

    Does not load the HID snippet in setup_class because the snippet needs to
    be loaded after guest mode is enabled.
    """
    super().setup_test()  # pylint: disable=attribute-error
    self.plug_in_hid_emulator()
    self.initialize_hid_emulator()

  def teardown_test(self):
    """Unplugs the HID emulator and unloads the HID snippet."""
    if hasattr(self, 'hid'):
      self.hid.cleanup()
    super().teardown_test()  # pylint: disable=attribute-error

  def test_keyboard_in_guest_mode(self) -> None:
    """Verifies top row and character keys in Guest Mode."""
    self.dut.user_tools.guest_mode()
    # when a guest mode is entered, there is popup window "Touch & hold the
    # action key to search..." that may be taking the key events. Sending an ESC
    # key to dismiss it.
    self.emulator.keypress([hid_keys.Function.ESCAPE])
    # hid snippet needs to be loaded after guest mode is enabled
    self.hid = self.create(pasit_hid)
    self.verify_hid_emulator_devices(self.hid)
    self.validate_keyboard_input(self.hid)


if __name__ == '__main__':
  test_runner.main()
