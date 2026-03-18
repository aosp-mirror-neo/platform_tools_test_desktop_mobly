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

"""Verify DUT wakes from suspend on keyboard HID key press (Dock only)."""

import logging

from android.platform.test.annotations import DesktopTest
from lib.pasit import hid_emulator
from lib.pasit import hid_keys
from lib.pasit import pasit_device
from mobly import asserts
from mobly import test_runner
from pasit.hid import persistent_hid_base_test


@DesktopTest(
    cujs=[
        'b/352597856',  # Wake DUT from basic USB hub
        'b/471033230',  # Keyboard/mouse work after suspend/resume
    ],
)
class HIDWakeTest(persistent_hid_base_test.PersistentHIDBaseTest):
  """Wake DUT from suspend using keyboard HID (Dock path only)."""

  def teardown_test(self) -> None:
    if not self.dut.power_on_if_offline():
      # If the DUT was already online, perform the wakeup routine.
      self.dut.wakeup(wakeup_routine_only=True)
    super().teardown_test()  # pylint: disable=attribute-error

  def test_wake_on_keyboard_keypress(self) -> None:
    """Verify DUT wakes from suspend on key press.

    Suspend the DUT, then send a keyboard keypress to wake it up. Verify that
    the DUT wakes up and is online.
    """

    logging.info('Suspending DUT')
    self.dut.suspend()
    self.emulator.keypress([hid_keys.ArrowPad.ARROW_RIGHT])
    # TODO: b/378512640 - need subsequent key-press to wake DUT from suspend
    self.emulator.keypress([hid_keys.ArrowPad.ARROW_DOWN])
    self.emulator.keypress([hid_keys.ArrowPad.ARROW_LEFT])
    self.emulator.keypress([hid_keys.ArrowPad.ARROW_UP])

    self._verify_dut_woke_up('keyboard key press')

  def test_wake_on_mouse_click(self) -> None:
    """Verify DUT wakes from suspend on mouse click."""
    logging.info('Suspending DUT')
    self.dut.suspend()

    self.emulator.mouse_click(hid_emulator.MouseButton.LEFT)
    # need subsequent mouse-clicks to wake DUT from suspend
    self.emulator.mouse_click(hid_emulator.MouseButton.RIGHT)

    self._verify_dut_woke_up('mouse click')

  def _verify_dut_woke_up(self, action: str) -> None:
    try:
      self.dut.wait_for_device_online()
      logging.info('DUT woke up from suspend on %s', action)
    except pasit_device.PasitDeviceError:
      asserts.fail(f'DUT failed to wake on {action}')


if __name__ == '__main__':
  test_runner.main()
