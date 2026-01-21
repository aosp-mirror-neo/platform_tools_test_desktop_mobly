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

from lib.pasit import pasit_test
from lib.utils import functools
from mobly import asserts
from mobly import test_runner
from pasit.hid import hid_base_test


@functools.generate_tests
class HIDWakeTest(hid_base_test.HIDBaseTest):
  """Wake DUT from suspend using keyboard HID (Dock path only)."""

  def test_wake_on_keyboard_keypress(self) -> None:

    logging.info('Activating HID emulator on DOCK path')
    self.passport_host.activate_device_by_type(
        device_type=pasit_test.PasitTestClass.DEVICE_TYPE_HID,
    )
    asserts.assert_true(
        self.hid.get_hid_devices(),
        'Keyboard HID not detected on DOCK path',
    )
    logging.info('Suspending DUT')
    self.dut.suspend()
    asserts.assert_false(
        self.dut.is_device_online(),
        'DUT should be suspended',
    )
    logging.info('Sending keyboard key press to wake DUT')
    # DUT needs 2 keypresses in succession to wake from sleep
    self.emulator.keypress(['Enter', 'Enter'])
    try:
      self.dut.wait_for_device_online()
    except pasit_test.PasitDeviceError:
      asserts.fail('DUT failed to wake on keyboard key press')


if __name__ == '__main__':
  test_runner.main()
