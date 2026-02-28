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

"""Verify HID devices work at login and lock screen."""

from android.platform.test.annotations import DesktopTest
from lib.pasit import dut_state_manager
from lib.pasit import pasit_hid
from mobly import test_runner
from pasit.hid import hid_base_test


@DesktopTest(
    cujs=[
        'b/471032780',  # External keyboard/mouse functional after reboot
        'b/471031829',  # External keyboard/mouse functional after lock/unlock
    ],
)
class USBAuthTests(hid_base_test.HIDBaseTest):
  """Verifies keyboard functionality with USB host authorization.

  Newly connected USB peripherals are not automatically
  trusted and require some form of explicit authorization
  before they can fully interact with the system. Keyboard and other HID
  devices should not be impacted
  """

  hid: pasit_hid.PasitHID

  def setup_class(self) -> None:
    """Setup for the test class."""
    super().setup_class()
    self.hid = self.create(pasit_hid)

  def teardown_class(self):
    """Handle the teardown for the class."""
    if hasattr(self, 'hid'):
      self.hid.cleanup()
    super().teardown_class()

  def test_hid_on_login_screen(self) -> None:
    """Verify HID works after booting to login screen."""

    self.skip_if_servo_needed_and_not_configured(
        dut_state_manager.PowerState.OFF
    )
    with dut_state_manager.EnterStateAndReturnToPowerOn(
        self.dut, dut_state_manager.PowerState.OFF, login_on_power_on=False
    ):
      self.plug_in_hid_emulator()

    self.initialize_and_verify_hid_emulator(self.hid)

  def test_hid_on_lock_screen(self) -> None:
    """Verify HID is detected on lock screen."""

    self.dut.user_tools.lock()
    self.plug_in_hid_emulator_and_verify(self.hid)


if __name__ == '__main__':
  test_runner.main()
