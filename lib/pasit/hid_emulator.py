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

"""A class to represent a HID emulator."""

import logging

from lib.pasit.passport import passport_host


class HIDEmulator:
  """A class to represent a HID emulator."""

  class Error(Exception):
    """Base error class for HIDEmulator."""

  passport: passport_host.PassportHost
  device_id: str

  def __init__(self, passport: passport_host.PassportHost):
    self.passport = passport

  def initialize(self) -> None:
    """Initializes the HID emulator.

    This method discovers the unique device ID of the HID emulator connected
    to the Passport host. It's crucial to plug in the HID emulator before this
    method to ensure the HID emulator is visible to the DUT and can be properly
    identified.
    Make sure to call this method after re-pluggin the HID emulator or DUT power
    cycle or suspend/resume.

    Raises:
      Error: If exactly one HID device is not found connected to the Passport
        host.
    """
    hid_devices = self.passport.hid_client.get_hid_devices()
    logging.info('Passport HID devices: %s', hid_devices)
    if len(hid_devices) != 1:
      raise self.Error(
          'Expected 1 HID device connected to the Passport host, but found'
          f' {len(hid_devices)} devices. Check your testbed configuration to'
          ' ensure only one and only one HID device is connected to the'
          ' Passport host.'
      )
    self.device_id = hid_devices[0]

  def emulate_keypress(self, keys: list[str]) -> None:
    """Emulates a keypress on the HID emulator.

    Args:
      keys: The list of keys to emulate.

    Raises:
      Error: If the emulator is not initialized.
    """
    if not hasattr(self, 'device_id'):
      raise self.Error(
          'HID emulator is not initialized. Please call initialize() before'
          ' emulate_keypress().'
      )
    logging.info('Emulating keypress: %s', keys)
    self.passport.hid_client.send_keypress(self.device_id, keys)
