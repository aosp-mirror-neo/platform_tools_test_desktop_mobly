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


import re
from lib.pasit.base import base_pasit_display

DisplayResolution = base_pasit_display.BasePasitDisplay.DisplayResolution
InfoNotFoundError = base_pasit_display.BasePasitDisplay.InfoNotFoundError


class AndroidPasitDisplay(base_pasit_display.BasePasitDisplay):
  """PasitDisplay for Android devices."""

  def get_display_count(self) -> int:
    dut_displays = (
        self.controller.adb.shell('ls -1d /sys/class/drm/card?-*')
        .decode('utf-8')
        .splitlines()
    )
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

  def get_display_ids(self) -> list[str]:
    # example line:
    # mBaseDisplayInfo=DisplayInfo{"Built-in Screen", displayId 0, ...
    display_info_lines = self._get_display_info_lines()
    display_ids = []
    for line in display_info_lines:
      match = re.search(r'displayId (\d+)', line)
      if match:
        display_ids.append(match.group(1))
    return display_ids

  def get_display_resolution(self, display_id: str = '') -> DisplayResolution:
    # example line:
    # mBaseDisplayInfo=DisplayInfo{"Built-in Screen", displayId 0,...
    # ..., real 1920 x 1200, largest app 1920 x 1200, smallest app 1920 x 1200
    display_info_lines = self._get_display_info_lines()
    display_id_match = (
        f'displayId {display_id}' if display_id else 'Built-in Screen'
    )
    display_info_lines = [
        line for line in display_info_lines if display_id_match in line
    ]
    if len(display_info_lines) != 1:
      raise ValueError(
          f'Expected 1 display info line for {display_id}, but got'
          f' {len(display_info_lines)}'
      )

    resolution_match = re.search(r'real (\d+) x (\d+)', display_info_lines[0])
    if not resolution_match:
      raise InfoNotFoundError(
          f'Failed to get display resolution for {display_id_match}.'
      )

    width = int(resolution_match.group(1))
    height = int(resolution_match.group(2))
    return DisplayResolution(width, height)

  def _get_display_info_lines(self) -> list[str]:
    dumpsys_display_lines = (
        self.controller.adb.shell(['dumpsys', 'display']).decode().splitlines()
    )
    # example line:
    # mBaseDisplayInfo=DisplayInfo{"Built-in Screen", displayId 0, displayGroupId 0, FLAG_SECURE, FLAG_SUPPORTS_PROTECTED_BUFFERS...
    return [
        line for line in dumpsys_display_lines if 'mBaseDisplayInfo' in line
    ]
