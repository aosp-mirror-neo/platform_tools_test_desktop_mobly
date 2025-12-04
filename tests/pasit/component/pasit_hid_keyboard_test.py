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

"""A test that exercises PASIT HID keyboard functionality."""

import logging
from lib.pasit import hid_emulator
from lib.pasit import hid_keys
from lib.pasit import pasit_hid
from lib.pasit import pasit_test
from mobly import asserts
from mobly import test_runner


class PasitHIDKeyboardTest(pasit_test.PasitTestClass):
  """A test that exercises PASIT HID keyboard functionality."""

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

  def test_capture_alphanumeric_keys(self) -> None:
    self._verify_all_keys_captured([key for key in hid_keys.Alphanumeric])

  def test_capture_function_keys(self) -> None:
    self._verify_all_keys_captured([key for key in hid_keys.Function])

  def test_capture_arrow_pad_keys(self) -> None:
    self._verify_all_keys_captured([key for key in hid_keys.ArrowPad])

  def test_capture_control_pad_keys(self) -> None:
    self._verify_all_keys_captured([key for key in hid_keys.ControlPad])

  def test_capture_numpad_keys(self) -> None:
    self._verify_all_keys_captured([key for key in hid_keys.Numpad])

  def _verify_all_keys_captured(self, keys: list[str]) -> None:
    """Verifies that all keys are captured correctly.

    Args:
      keys: The list of keys to verify.
    """
    all_captured_keys = []
    all_expected_keys = []
    failed_keys = []
    for key in keys:
      try:
        self.emulator.keypress([key])
      except Exception as e:  # pylint: disable=broad-except
        logging.exception('Failed to emulate keypress %s: %s', key, e)
        failed_keys.append(key)
        continue
      all_captured_keys.append(self.hid.get_captured_key_events())
      all_expected_keys.append(self.hid.get_expected_key_events(key))
    asserts.assert_equal(all_expected_keys, all_captured_keys)
    asserts.assert_equal(
        [], failed_keys, f'Failed to capture keys: {failed_keys}'
    )


if __name__ == '__main__':
  test_runner.main()
