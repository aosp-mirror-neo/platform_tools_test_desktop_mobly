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

"""A test that exercises PASIT HID functionality."""

from lib.pasit import hid_emulator
from lib.pasit import pasit_hid
from lib.pasit import pasit_test
from mobly import asserts
from mobly import test_runner


class PasitHIDTest(pasit_test.PasitTestClass):
  """A test that exercises PASIT HID functionality."""

  hid: pasit_hid.PasitHID
  emulator: hid_emulator.HIDEmulator

  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_HID

  def setup_class(self):
    super().setup_class()
    self.hid = self.create(pasit_hid)
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_HID)
    self.emulator = hid_emulator.HIDEmulator(self.passport_host)
    self.emulator.initialize()

  def setup_test(self):
    """Handle the setup for the test."""
    super().setup_test()
    # Start key capture on the DUT.
    self.hid.start_key_capture()

  def teardown_test(self):
    """Handle the teardown for the test."""
    self.hid.stop_key_capture()
    # avoid passport reset in PasitTestClass.teardown_test
    # super().teardown_test()

  def test_capture_characters_keys(self) -> None:
    self.emulator.emulate_keypress(['S'])
    captured_keys = self.hid.get_captured_keys()
    asserts.assert_equal(
        captured_keys,
        ['DOWN: KEYCODE_S', 'UP: KEYCODE_S'],
        'Expected to capture key events from DUT.',
    )

  def test_capture_top_row_keys(self) -> None:
    self.emulator.emulate_keypress(['F1'])
    captured_keys = self.hid.get_captured_keys()
    asserts.assert_equal(
        captured_keys,
        ['DOWN: KEYCODE_F1', 'UP: KEYCODE_F1'],
        'Expected to capture key events from DUT.',
    )

  def test_capture_special_keys(self) -> None:
    self.emulator.emulate_keypress(['Home'])
    captured_keys = self.hid.get_captured_keys()
    asserts.assert_equal(
        captured_keys,
        ['DOWN: KEYCODE_MOVE_HOME', 'UP: KEYCODE_MOVE_HOME'],
        'Expected to capture key events from DUT.',
    )


if __name__ == '__main__':
  test_runner.main()
