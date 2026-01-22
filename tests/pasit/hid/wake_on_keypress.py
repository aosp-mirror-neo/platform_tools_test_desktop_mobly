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

from lib.pasit import hid_keys
from lib.pasit import pasit_device
from mobly import asserts
from mobly import records
from mobly import test_runner
from pasit.hid import hid_base_test


class HIDWakeTest(hid_base_test.HIDBaseTest):
  """Wake DUT from suspend using keyboard HID (Dock path only)."""

  def on_fail(self, record: records.TestResultRecord) -> None:
    # If the test fails, make sure the DUT is awake and online before the next
    # test runs. The teardown_test method of the PasitTestClass is not called
    # in the HIDBaseTest so the recovery routine is not run.
    if hasattr(self, 'dut'):
      self.dut.wakeup()
    super().on_fail(record)

  def test_wake_on_keyboard_keypress(self) -> None:
    """Verify DUT wakes from suspend on key press.

    Suspend the DUT, then send a keyboard keypress to wake it up. Verify that
    the DUT wakes up and is online.
    """

    logging.info('Suspending DUT')
    self.dut.suspend()
    self.emulator.keypress([hid_keys.Alphanumeric.ENTER])
    # TODO: b/378512640 - need subsequent key-press to wake DUT from suspend
    self.emulator.keypress([hid_keys.Alphanumeric.ENTER])

    logging.info('Waiting for DUT to wake up from suspend...')
    try:
      self.dut.wait_for_device_online()
    except pasit_device.PasitDeviceError:
      asserts.fail('DUT failed to wake on keyboard key press')

    logging.info('DUT woke up from suspend on keyboard key press')


if __name__ == '__main__':
  test_runner.main()
