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

"""AndroidPasitDisplay handles display operations for PASIT testing on Android devices."""

from mobly.controllers import android_device

from pasit.lib.base import base_pasit_display


class AndroidPasitDisplay(base_pasit_display.BasePasitDisplay):
  """PasitDisplay for Android devices."""

  def get_display_count(self) -> int:
    try:
      dut_displays = (
          self.controller.adb.shell('ls -1d /sys/class/drm/card?-*')
          .decode('utf-8')
          .splitlines()
      )
    except android_device.adb.AdbError:
      # The command fails when grep returns empty. Catch the error and return
      # 0.
      return 0
    display_count = 0
    for display in dut_displays:
      display = display.strip()
      status = (
          self.controller.adb.shell(['cat', f'{display}/status'])
          .decode('utf-8')
          .strip()
      )
      if status == 'connected':
        display_count += 1
    return display_count
