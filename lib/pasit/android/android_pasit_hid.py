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

"""AndroidPasitHID handles HID operations for PASIT testing on Android devices."""

import logging
import os
import sys
from typing import List

from lib.pasit.base import base_pasit_hid
from mobly.controllers import android_device
from mobly.controllers.android_device_lib import apk_utils


class AndroidPasitHID(base_pasit_hid.BasePasitHID):
  """PasitHID for Android devices."""

  KeyboardShortcut = base_pasit_hid.BasePasitHID.KeyboardShortcut

  HID_SNIPPET_PACKAGE_NAME = 'com.google.android.hiddevicesnippet'
  HID_SNIPPET_APK_PATH = os.path.join(
      os.path.dirname(os.path.abspath(sys.argv[0])),
      'HidDeviceSnippet.apk',
  )

  def __init__(self, controller: android_device.AndroidDevice):
    """Initializes the AndroidPasitHID."""
    super().__init__(controller)
    apk_utils.install(
        self.controller,
        self.HID_SNIPPET_APK_PATH,
    )
    self.controller.load_snippet('hid', self.HID_SNIPPET_PACKAGE_NAME)

  def cleanup(self):
    """Cleans up after testing.

    Uninstalls the HidDeviceSnippet when the object is garbage collected.
    """
    self.controller.unload_snippet('hid')
    apk_utils.uninstall(self.controller, self.HID_SNIPPET_PACKAGE_NAME)

  def get_hid_devices(self) -> List[base_pasit_hid.BasePasitHID.DeviceInfo]:
    """Returns a list of connected HID devices using the Mobly snippet."""
    if not isinstance(self.controller, android_device.AndroidDevice):
      raise TypeError(
          'AndroidPasitHID requires an AndroidDevice controller, but got'
          f' {type(self.controller)}'
      )

    try:
      devices_json = self.controller.hid.getHidDevices()
    except Exception as e:
      # Handle potential errors during RPC call (e.g., snippet not loaded)
      raise RuntimeError('Failed to get HID devices from snippet.') from e
    hid_devices: List[base_pasit_hid.BasePasitHID.DeviceInfo] = []
    for device_info in devices_json:
      # The snippet returns a list of dictionaries.
      # Convert each dictionary to our HidDeviceInfo dataclass.
      hid_devices.append(
          base_pasit_hid.BasePasitHID.DeviceInfo(
              name=device_info['name'],
              vendor_id=device_info['vendorId'],
              product_id=device_info['productId'],
              type=device_info['type'],
          )
      )
    logging.debug('HID devices: %s', hid_devices)
    return hid_devices

  def get_shortcut_combination(self, shortcut: KeyboardShortcut) -> List[str]:
    match shortcut:
      case self.KeyboardShortcut.SCREENSHOT:
        return ['Meta', 'S']
      case self.KeyboardShortcut.SETTINGS:
        return ['Meta', 'I']
      case self.KeyboardShortcut.HOME:
        return ['Meta', 'H']
      case _:
        raise ValueError(f'Unsupported shortcut: {shortcut}')
