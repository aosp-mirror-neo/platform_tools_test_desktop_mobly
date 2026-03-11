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

  def initialize_hid_emulator(self) -> None:
    """Initializes the HID emulator.

    Retries the initialization based on the retry policy until successful.

    Raises:
      hid_emulator.HIDEmulator.Error: If the HID emulator fails to initialize.
    """
    retry.retry(
        self.emulator.initialize,
        policy=test_policy.HIDTestPolicy.DETECT_HID_EMULATOR_RETRY_POLICY,
        exceptions=(hid_emulator.HIDEmulator.Error,),
    )

  def verify_hid_emulator_devices(self, hid: pasit_hid.PasitHID) -> None:
    """Verifies the HID emulator devices are seen by the DUT.

    Args:
      hid: The PasitHID object to use for verifying the HID emulator devices.
    """
    # TODO: b/490154651 - Replace this with retry with
    # DETECT_EXTERNAL_HID_DEVICES_RETRY_POLICY once the bug is fixed.
    hid_emulator_devices = retry.wait_for_stable_value(
        hid.get_hid_emulator_devices,
        timeout_seconds=test_policy.HIDTestPolicy.STABLE_TIMEOUT_SECONDS,
        delay_seconds=test_policy.HIDTestPolicy.STABLE_POLLING_INTERVAL_SECONDS,
        required_stable_duration_seconds=test_policy.HIDTestPolicy.STABLE_REQUIRED_DURATION_SECONDS,
        criteria=lambda devices: len(devices)
        == test_policy.HIDTestPolicy.NUM_HID_DEVICES_EXPECTED,
    )
    logging.info('HID emulator devices seen by DUT: %s', hid_emulator_devices)

  def plug_in_hid_emulator(self) -> None:
    """Plugs in the HID emulator to the DUT."""
    logging.info('Plugging in HID emulator to DUT')
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_HID)

  def unplug_hid_emulator(self) -> None:
    """Un-plugs the HID emulator from the DUT."""
    logging.info('Unplugging HID emulator from DUT')
    self.passport_host.deactivate_device_by_type(self.DEVICE_TYPE_HID)

  def initialize_and_verify_hid_emulator(self, hid: pasit_hid.PasitHID) -> None:
    """Initializes and verifies the HID emulator."""
    self.initialize_hid_emulator()
    self.verify_hid_emulator_devices(hid)

  def plug_in_hid_emulator_and_verify(self, hid: pasit_hid.PasitHID) -> None:
    """Plugs in the HID emulator to the DUT and initializes it."""
    self.plug_in_hid_emulator()
    self.initialize_and_verify_hid_emulator(hid)

  def validate_keyboard_input(self, hid: pasit_hid.PasitHID) -> None:
    """Validates keyboard input for function and alphanumeric keys."""
    hid.start_key_capture()
    self.capture_screenshots('key_capture_started')

    logging.info('Validating keyboard input...')
    for key_enum in (hid_keys.Function, hid_keys.Alphanumeric):
      logging.info('Verifying %s keys...', key_enum.__name__)
      self._verify_all_keys_captured(hid, key_enum)
    logging.info('Keyboard input validation complete.')

    hid.stop_key_capture()

  def _verify_all_keys_captured(
      self, hid: pasit_hid.PasitHID, keys: enum.StrEnum
  ) -> None:
    """Iterates through keys and asserts they are captured by the DUT."""
    for key in keys:
      self._verify_single_key_captured(hid, key)

  def _verify_single_key_captured(
      self, hid: pasit_hid.PasitHID, key: str
  ) -> None:
    """Verifies a single key is captured by the DUT."""
    self.emulator.keypress([key])
    captured = hid.get_captured_key_events()
    expected = hid.get_expected_key_events(key)
    asserts.assert_equal(expected, captured, f'Key events mismatch for {key}')
