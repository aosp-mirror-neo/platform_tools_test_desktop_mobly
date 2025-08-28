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

"""Parser for dumpsys surfaceflinger output."""

import logging
import re
from lib.pasit.android import android_display_id
from lib.pasit.base import base_pasit_display
from mobly.controllers import android_device

DisplayId = android_display_id.AndroidDisplayId
DisplayResolution = base_pasit_display.BasePasitDisplay.DisplayResolution
InfoNotFoundError = base_pasit_display.BasePasitDisplay.InfoNotFoundError


class DumpsysSurfaceFlingerParser:
  """Parser for dumpsys surfaceflinger output.

  Executes `adb shell dumpsys SurfaceFlinger` and parses the output in the
  constructor. Each method returns information from the dumpsys surfaceflinger
  output about a specific display.
  """

  def __init__(self, controller: android_device.AndroidDevice):
    self.controller = controller
    self.dumpsys_surfaceflinger_lines = (
        self.controller.adb.shell(['dumpsys', 'SurfaceFlinger'])
        .decode()
        .splitlines()
    )

  def get_supported_display_resolutions(
      self, display_id: DisplayId
  ) -> dict[str, DisplayResolution]:
    display_info_lines = self._get_display_info_lines(display_id.unique_id)
    logging.debug('display_info_lines: %s', display_info_lines)
    result = {}
    display_modes_block_started = False
    for line in display_info_lines:
      if 'displayModes=' in line:
        display_modes_block_started = True
      elif display_modes_block_started:
        # {id=0, hwcId=44, resolution=1920x1080, vsyncRate=60.00 Hz, dpi=101.60x101.60, group=1, vrrConfig=N/A, supportedHdrTypes=SYSTEM}
        match = re.search(
            r'id=(\d+).*resolution=(\d+)x(\d+)',
            line,
        )
        if match:
          result[match.group(1)] = DisplayResolution(
              int(match.group(2)), int(match.group(3))
          )
        else:
          # end of the display modes block, ignore the rest of the lines
          break
    return result

  def _get_display_info_lines(self, display_unique_id: str) -> list[str]:
    result = []
    display_info_block_started = False
    for line in self.dumpsys_surfaceflinger_lines:
      if line == f'Display {display_unique_id}':
        display_info_block_started = True
      elif display_info_block_started:
        if not line.strip():
          # empty line indicates the end of the display info block,
          # ignore the rest of the lines
          return result
        else:
          # otherwise, add the line to the result
          result.append(line)
    return []
