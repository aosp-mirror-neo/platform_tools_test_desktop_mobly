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

"""Base class for HID tests."""

import enum
import logging
from lib.pasit import hid_emulator
from lib.pasit import hid_keys
from lib.pasit import pasit_hid
from lib.pasit import pasit_test
from lib.pasit import test_policy
from lib.utils import retry
from mobly import asserts


class HIDBaseTest(pasit_test.PasitTestClass):
  """Test for HID functionality.

  Doesn't plug in or unplug the HID emulator, only provides helper methods for
  tests that do.
  Creates the emulator in setup_class.
  """

  emulator: hid_emulator.HIDEmulator

  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_HID

  def setup_class(self):
    """Handle the setup for the test."""
    super().setup_class()
    self.emulator = hid_emulator.HIDEmulator(self.passport_host)

  def plug_in_hid_emulator_and_verify(self, hid: pasit_hid.PasitHID) -> None:
    """Plugs in the HID emulator to the DUT and initializes it."""
    self.plug_in_hid_emulator()
    retry.retry(
        self.emulator.initialize,
        policy=test_policy.HIDTestPolicy.DETECT_HID_EMULATOR_RETRY_POLICY,
        exceptions=(hid_emulator.HIDEmulator.Error,),
    )
    hid_emulator_devices = retry.retry(
        hid.get_hid_emulator_devices,
        until=lambda hid_devices: len(hid_devices)
        == test_policy.HIDTestPolicy.NUM_HID_DEVICES_EXPECTED,
        policy=test_policy.HIDTestPolicy.DETECT_EXTERNAL_HID_DEVICES_RETRY_POLICY,
    )
    logging.info('HID emulator devices seen by DUT: %s', hid_emulator_devices)
    asserts.assert_equal(
        len(hid_emulator_devices),
        test_policy.HIDTestPolicy.NUM_HID_DEVICES_EXPECTED,
        'Expected DUT to have'
        f' {test_policy.HIDTestPolicy.NUM_HID_DEVICES_EXPECTED} HID emulator'
        ' devices after activation of HID emulator.',
    )

  def plug_in_hid_emulator(self) -> None:
    """Plugs in the HID emulator to the DUT."""
    logging.info('Plugging in HID emulator to DUT')
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_HID)

  def _verify_all_keys_captured(
      self, hid: pasit_hid.PasitHID, keys: enum.StrEnum
  ) -> None:
    """Iterates through keys and asserts they are captured by the DUT."""
    for key in keys:
      self.emulator.keypress([key])
      captured = hid.get_captured_key_events()
      expected = hid.get_expected_key_events(key)
      asserts.assert_equal(captured, expected, f'Key events mismatch for {key}')

  def unplug_hid_emulator(self) -> None:
    """Un-plugs the HID emulator from the DUT."""
    logging.info('Unplugging HID emulator from DUT')
    self.passport_host.deactivate_device_by_type(self.DEVICE_TYPE_HID)

  def validate_keyboard_input(self, hid: pasit_hid.PasitHID) -> None:
    """Validates keyboard input for function and alphanumeric keys."""
    self.hid.start_key_capture()
    self.capture_screenshots('key_capture_started')

    logging.info('Validating keyboard input...')
    for key_enum in (hid_keys.Function, hid_keys.Alphanumeric):
      logging.info('Verifying %s keys...', key_enum.__name__)
      self._verify_all_keys_captured(hid, key_enum)
    logging.info('Keyboard input validation complete.')

    self.hid.stop_key_capture()
