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
from typing import TypeAlias

from chromiumos.test.lab.api.passport import hid_service_pb2
from lib.pasit.passport import passport_host


MouseButton: TypeAlias = hid_service_pb2.MouseActionRequest.Button


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

  def keypress(self, keys: list[str]) -> None:
    """Emulates a keypress on the HID emulator.

    Args:
      keys: The list of keys to emulate. If more than one key is provided, they
        will be pressed as a key combination.

    Raises:
      Error: If the emulator is not initialized.
    """

    self._ensure_initialized()
    logging.info('Emulating keypress: %s', keys)
    self.passport.hid_client.send_keypress(self.device_id, keys)

  def mouse_click(self, button: MouseButton) -> None:
    """Emulates a mouse button press on the HID emulator.

    Args:
      button: The mouse button to emulate.

    Raises:
      Error: If the emulator is not initialized.
    """
    self._ensure_initialized()
    logging.info('Emulating mouse button press: %s', MouseButton.Name(button))
    self.passport.hid_client.send_mouse_click(self.device_id, button)

  def mouse_move(self, x: int, y: int) -> None:
    """Emulates a mouse move on the HID emulator.

    The x and y values are passed to HID service of the Passport API directly.
    Please refer to the HID service API documentation for more details on
    how the values are interpreted.

    Args:
      x: The distance to move a mouse pointer by in a horizontal axis.
      y: The distance to move a mouse pointer by in a vertical axis.

    Raises:
      Error: If the emulator is not initialized.
    """
    self._ensure_initialized()
    logging.info('Emulating mouse move: (%d, %d)', x, y)
    self.passport.hid_client.send_mouse_move(self.device_id, x, y)

  def mouse_scroll(self, distance: int) -> None:
    """Emulates a mouse scroll on the HID emulator.

    The distance is passed to HID service of the Passport API directly.
    Please refer to the HID service API documentation for more details on
    how the value is interpreted.

    Args:
      distance: The distance to scroll by. Positive values scroll up and
        negative values scroll down.

    Raises:
      Error: If the emulator is not initialized.
    """
    self._ensure_initialized()
    logging.info('Emulating mouse scroll: %d', distance)
    self.passport.hid_client.send_mouse_scroll(self.device_id, distance)

  def _ensure_initialized(self) -> None:
    """Ensures the emulator is initialized.

    Raises:
      Error: If the emulator is not initialized.
    """
    if not hasattr(self, 'device_id'):
      raise self.Error(
          'HID emulator is not initialized. Please call initialize() before'
          ' using the emulator.'
      )
