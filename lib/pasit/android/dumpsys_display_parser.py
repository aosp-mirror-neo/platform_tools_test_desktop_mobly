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

"""Parser for dumpsys display output."""

import re
from lib.pasit.android import android_display_id
from lib.pasit.base import base_pasit_display
from mobly.controllers import android_device

DisplayId = android_display_id.AndroidDisplayId
DisplayResolution = base_pasit_display.BasePasitDisplay.DisplayResolution
InfoNotFoundError = base_pasit_display.BasePasitDisplay.InfoNotFoundError


class DumpsysDisplayParser:
  """Parser for dumpsys display output.

  Executes `adb shell dumpsys display` and parses the output in the constructor.
  Each method returns information from the dumpsys display output about
  a specific display or the built-in display if no display ID is provided.
  """

  def __init__(self, controller: android_device.AndroidDevice):
    self.controller = controller
    self.dumpsys_display_lines = (
        self.controller.adb.shell(['dumpsys', 'display']).decode().splitlines()
    )

  def get_display_ids(self) -> list[DisplayId]:
    """Returns the display IDs."""
    display_ids = []
    for base_display_info_line in self._get_base_display_info():
      display_id = self._get_display_id_from_display_info_line(
          base_display_info_line
      )
      display_ids.append(display_id)
    return display_ids

  def get_display_resolution(
      self, display_id: DisplayId | None = None
  ) -> DisplayResolution:
    # ..., real 1920 x 1200, largest app 1920 x 1200, smallest app 1920 x 1200
    display_info_line = self._get_display_info_line(display_id)
    resolution_match = re.search(r'real (\d+) x (\d+)', display_info_line)
    if not resolution_match:
      raise InfoNotFoundError(
          f'Failed to get display resolution for display id "{display_id}".'
      )
    width = int(resolution_match.group(1))
    height = int(resolution_match.group(2))
    return DisplayResolution(width, height)

  def get_supported_display_resolutions(
      self, display_id: DisplayId | None = None
  ) -> dict[str, DisplayResolution]:
    # supportedModes [{id=3, width=1920, height=1080, fps=60.0, vsync=60.0,
    # synthetic=false, alternativeRefreshRates=[], supportedHdrTypes=[]}, ...]
    display_info_line = self._get_display_info_line(display_id)
    supported_modes_match = re.search(
        r'supportedModes \[((\{.*?\})+)\]', display_info_line
    )
    if not supported_modes_match:
      raise InfoNotFoundError(
          'Failed to get supported display resolutions for display id'
          f' "{display_id}".'
      )
    supported_modes = supported_modes_match.group(1)
    matches = re.findall(
        r'id=(\d+),.*?width=(\d+),.*?height=(\d+)', supported_modes
    )
    return {
        match[0]: DisplayResolution(int(match[1]), int(match[2]))
        for match in matches
    }

  def get_internal_display_id(self) -> DisplayId:
    """Returns the internal display ID."""
    display_info_line = self._get_display_info_line()
    return self._get_display_id_from_display_info_line(display_info_line)

  def _get_base_display_info(self) -> list[str]:
    # example line:
    # mBaseDisplayInfo=DisplayInfo{"Built-in Screen", displayId 0...
    return [
        line
        for line in self.dumpsys_display_lines
        if 'mBaseDisplayInfo' in line
    ]

  def _get_display_id_from_display_info_line(
      self, display_info_line: str
  ) -> DisplayId:
    matchId = re.search(r'displayId (\d+)', display_info_line)
    matchUniqueId = re.search(r'uniqueId \"local:(\d+)\"', display_info_line)
    if matchId and matchUniqueId:
      return DisplayId(
          display_id=matchId.group(1), unique_id=matchUniqueId.group(1)
      )
    else:
      raise ValueError(
          'Failed to get display id from display info line:'
          f' {display_info_line}'
      )

  def _get_display_info_line(self, display_id: DisplayId | None = None) -> str:
    """Returns the display info line for the given display ID.

    Args:
      display_id: The display ID to get the info line for. If not specified, the
        info line for the built-in display will be returned.

    Returns:
      The display info line for the given display ID. Example line:
      mBaseDisplayInfo=DisplayInfo{"Built-in Screen", displayId 0, ...
    """
    display_info_lines = self._get_base_display_info()
    display_id_match = (
        f'displayId {display_id}' if display_id else 'Built-in Screen'
    )
    display_info_lines = [
        line for line in display_info_lines if display_id_match in line
    ]
    if len(display_info_lines) != 1:
      raise ValueError(
          f'Expected 1 display info line for {display_id_match}, but got'
          f' {len(display_info_lines)}'
      )
    return display_info_lines[0]
