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

"""Library for interacting with Thunderbolt/USB4 sysfs on Android devices."""

import logging
import pathlib
from typing import List, Optional

from mobly.controllers import android_device
from mobly.controllers.android_device_lib import adb


class ThunderboltSysfs:
  """Helper class to interact with Thunderbolt/USB4 sysfs."""

  _TBT_PATH = pathlib.PurePosixPath('/sys/bus/thunderbolt')
  _TBT_DEVS_PATH = _TBT_PATH / 'devices'

  def __init__(self, ad: android_device.AndroidDevice):
    self._ad = ad
    self._ad.adb = self._ad.controller.adb

  def get_all_devices(self) -> List[str]:
    """Returns a list of all Thunderbolt device IDs (e.g., 0-0, 0-1)."""
    try:
      return (
          self._ad.adb.shell(f'ls {self._TBT_DEVS_PATH}')
          .decode('utf-8')
          .split()
      )
    except adb.AdbError:
      return []

  def get_device_attribute(self, device_id: str, attribute: str) -> str:
    """Reads a specific attribute for a given device ID."""
    path = self._TBT_DEVS_PATH / device_id / attribute
    try:
      return self._ad.adb.shell(f'cat {path}').decode('utf-8').strip()
    except adb.AdbError as e:
      logging.warning('Failed to read %s for %s: %s', attribute, device_id, e)
      return ''

  def get_device_name(self, device_id: str) -> str:
    return self.get_device_attribute(device_id, 'device_name')

  def get_vendor_name(self, device_id: str) -> str:
    return self.get_device_attribute(device_id, 'vendor_name')

  def get_device_generation(self, device_id: str) -> int:
    return int(self.get_device_attribute(device_id, 'generation'))

  def is_authorized(self, device_id: str) -> bool:
    val = self.get_device_attribute(device_id, 'authorized')
    return val == '1'

  def find_device_by_name_substring(self, name_substr: str) -> Optional[str]:
    """Finds a device ID where the device_name contains the substring."""
    devices = self.get_all_devices()
    for dev in devices:
      # Filter out domains (domain0, domain1...) and xdomains (0-0:1...)
      # Typically devices look like 0-0, 0-1, 0-301.
      # Domains look like domain0, xdomains look like 0-0:1.
      if 'domain' in dev or ':' in dev:
        continue

      name = self.get_device_name(dev)
      logging.debug(
          'Matching %s to device %s with name %s', name_substr, dev, name
      )
      if name_substr in name:
        return dev
    return None
