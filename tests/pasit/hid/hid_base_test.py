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

import logging

from lib.pasit import hid_emulator
from lib.pasit import hid_keys
from lib.pasit import pasit_hid
from lib.pasit import pasit_test
from lib.pasit import test_policy
from lib.utils import retry
from mobly import asserts


class HIDBaseTest(pasit_test.PasitTestClass):
  """Test for HID functionality."""

  hid: pasit_hid.PasitHID
  emulator: hid_emulator.HIDEmulator

  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_HID

  def setup_class(self):
    """Handle the setup for the test."""
    super().setup_class()
    self.hid = self.create(pasit_hid)
    default_hid_devices = self.hid.get_hid_devices()

    self.plug_in_hid_emulator()
    self.emulator = hid_emulator.HIDEmulator(self.passport_host)
    retry.retry(
        self.emulator.initialize,
        policy=test_policy.HIDTestPolicy.DETECT_HID_EMULATOR_RETRY_POLICY,
        exceptions=(hid_emulator.HIDEmulator.Error,),
    )

    self._verify_hid_emulator_is_visible_to_dut(default_hid_devices)

  def _verify_hid_emulator_is_visible_to_dut(
      self, default_hid_devices: list[str]
  ) -> None:
    updated_hid_devices = retry.retry(
        self.hid.get_hid_emulator_devices,
        until=lambda hid_devices: len(hid_devices)
        == len(default_hid_devices)
        + test_policy.HIDTestPolicy.NUM_HID_DEVICES_EXPECTED,
        policy=test_policy.HIDTestPolicy.DETECT_EXTERNAL_HID_DEVICES_RETRY_POLICY,
    )
    new_hid_devices = [
        dev for dev in updated_hid_devices if dev not in default_hid_devices
    ]
    logging.info('New HID devices seen by DUT: %s', new_hid_devices)
    asserts.assert_equal(
        len(new_hid_devices),
        test_policy.HIDTestPolicy.NUM_HID_DEVICES_EXPECTED,
        'Expected DUT to have'
        f' {test_policy.HIDTestPolicy.NUM_HID_DEVICES_EXPECTED} new HID devices'
        ' after activation of HID emulator.',
    )

  def teardown_class(self):
    """Handle the teardown for the class."""
    if hasattr(self, 'hid'):
      self.hid.cleanup()
    super().teardown_class()

  def teardown_test(self):
    # ensure that switches are not disabled between tests by not calling the
    # super class teardown_test.
    pass

  def plug_in_hid_emulator(self) -> None:
    """Plugs in the HID emulator to the DUT."""
    logging.info('Plugging in HID emulator to DUT')
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_HID)

  def verify_all_keys_captured(
      self, emulator: hid_emulator.HIDEmulator, keys: list[str]
  ) -> None:
    """Iterates through keys and asserts they are captured by the DUT."""
    for key in keys:
      emulator.keypress([key])
      captured = self.hid.get_captured_key_events()
      expected = self.hid.get_expected_key_events(key)
      asserts.assert_equal(captured, expected, f'Key events mismatch for {key}')

  def unplug_hid_emulator(self) -> None:
    """Un-plugs the HID emulator from the DUT."""
    logging.info('Unplugging HID emulator from DUT')
    self.passport_host.deactivate_device_by_type(self.DEVICE_TYPE_HID)

  def _validate_keyboard_input(
      self, emulator: hid_emulator.HIDEmulator
  ) -> None:
    """Validates keyboard input for function and alphanumeric keys."""
    logging.info('Validating keyboard input...')
    logging.info('Verifying function keys...')
    self.verify_all_keys_captured(emulator, [key for key in hid_keys.Function])
    logging.info('Verifying alphanumeric keys...')
    self.verify_all_keys_captured(
        self.emulator, [key for key in hid_keys.Alphanumeric]
    )
    logging.info('Keyboard input validation complete.')
