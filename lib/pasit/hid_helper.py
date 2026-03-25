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

"""Helper class for HID testing tools for PASIT tests."""

import logging

from lib.pasit import hid_emulator
from lib.pasit import pasit_hid
from lib.pasit import test_policy
from lib.utils import retry


class HIDHelper:
  """Helper class for HID operations."""

  def __init__(self, emulator: hid_emulator.HIDEmulator):
    self.emulator = emulator

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

  def wait_for_hid_connected(self, hid: pasit_hid.PasitHID) -> None:
    """Waits for the HID emulator to be connected to the DUT.

    Args:
      hid: The PasitHID object to use for verifying the HID emulator devices.

    Raises:
      retry.StabilizationTimeoutError: If the HID emulator does not connect to
        the DUT within the timeout.
    """
    # TODO: b/491864518 - Replace this with retry with
    # DETECT_EXTERNAL_HID_DEVICES_RETRY_POLICY once the bug is fixed.
    hid_emulator_devices = retry.wait_for_stable_value(
        lambda: self._get_hid_emulator_devices(hid),
        timeout_seconds=test_policy.HIDTestPolicy.STABLE_TIMEOUT_SECONDS,
        delay_seconds=test_policy.HIDTestPolicy.STABLE_POLLING_INTERVAL_SECONDS,
        required_stable_duration_seconds=test_policy.HIDTestPolicy.STABLE_REQUIRED_DURATION_SECONDS,
        criteria=lambda devices: len(devices)
        == test_policy.HIDTestPolicy.NUM_HID_DEVICES_EXPECTED,
        value_name='HID emulator devices',
    )
    logging.info('HID emulator devices seen by DUT: %s', hid_emulator_devices)

  def _get_hid_emulator_devices(
      self, hid: pasit_hid.PasitHID
  ) -> list[pasit_hid.PasitHID.DeviceInfo]:
    """Returns the HID emulator devices connected to the DUT."""
    logging.debug(
        'Passport HID devices: %s', self.emulator.get_hid_emulator_devices()
    )
    return hid.get_hid_emulator_devices()
