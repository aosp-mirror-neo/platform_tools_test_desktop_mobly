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

"""Parser for dumpsys battery output."""

import re
from mobly.controllers import android_device


class DumpsysBatteryParser:
  """Parser for dumpsys battery output.

  Executes `adb shell dumpsys battery` and parses the output in the constructor.
  Each method returns information from the dumpsys battery output.
  """

  AC_POWERED_REGEX = re.compile(r'\s+AC powered: (\w+)')
  USB_POWERED_REGEX = re.compile(r'\s+USB powered: (\w+)')
  WIRELESS_POWERED_REGEX = re.compile(r'\s+Wireless powered: (\w+)')
  DOCK_POWERED_REGEX = re.compile(r'\s+Dock powered: (\w+)')

  def __init__(self, controller: android_device.AndroidDevice):
    self.ac_powered = False
    self.usb_powered = False
    self.wireless_powered = False
    self.dock_powered = False

    self.controller = controller
    self.dumpsys_battery_lines = (
        self.controller.adb.shell(['dumpsys', 'battery']).decode().splitlines()
    )
    self._parse_powered_state()

  def is_powered(self) -> bool:
    """Returns True if the device is powered."""
    return (
        self.ac_powered
        or self.usb_powered
        or self.wireless_powered
        or self.dock_powered
    )

  def _parse_powered_state(self):
    """Parses the powered state from the dumpsys battery output."""
    for line in self.dumpsys_battery_lines:
      if self._is_key_value_true(line, self.AC_POWERED_REGEX):
        self.ac_powered = True
      if self._is_key_value_true(line, self.USB_POWERED_REGEX):
        self.usb_powered = True
      if self._is_key_value_true(line, self.WIRELESS_POWERED_REGEX):
        self.wireless_powered = True
      if self._is_key_value_true(line, self.DOCK_POWERED_REGEX):
        self.dock_powered = True

  def _is_key_value_true(self, line: str, regex: re.Pattern[str]) -> bool:
    """Returns True if the line is a key value pair."""
    match = regex.match(line)
    if match:
      return match.group(1) == 'true'
    return False
