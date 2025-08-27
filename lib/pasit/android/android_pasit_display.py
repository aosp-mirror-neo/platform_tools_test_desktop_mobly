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


import logging
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
    return self._get_display_ids_from_dumpsys_display()

  def get_display_resolution(self, display_id: str = '') -> DisplayResolution:
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
      self, display_id: str = ''
  ) -> dict[str, DisplayResolution]:
    # supportedModes [{id=3, width=1920, height=1080, fps=60.0, vsync=60.0,
    # synthetic=false, alternativeRefreshRates=[], supportedHdrTypes=[]}, ...]
    display_info_line = self._get_display_info_line(display_id)
    supported_modes_match = re.search(
        r'supportedModes \[((\{.*?\})+)\]', display_info_line
    )
    if not supported_modes_match:
      raise InfoNotFoundError(
          f'Failed to get supported display resolutions for display id'
          f' "{{display_id}}".'
      )

    supported_modes = supported_modes_match.group(1)
    logging.debug('supportedModes: %s', supported_modes)
    matches = re.findall(
        r'id=(\d+),.*?width=(\d+),.*?height=(\d+)', supported_modes
    )
    return {
        match[0]: DisplayResolution(int(match[1]), int(match[2]))
        for match in matches
    }

  def set_night_light_enabled(self, enabled: bool):
    self.controller.adb.shell([
        'settings',
        'put',
        'secure',
        'night_display_activated',
        '1' if enabled else '0',
    ])

  def get_night_light_enabled(self) -> bool:
    # night_display_activated is 1 if night light is enabled, 0 otherwise.
    return (
        self.controller.adb.shell([
            'settings',
            'get',
            'secure',
            'night_display_activated',
        ])
        .decode('utf-8')
        .strip()
        .lower()
        .startswith('1')
    )

  def set_night_light_temperature(self, temperature: int):
    self.controller.adb.shell([
        'settings',
        'put',
        'secure',
        'night_display_color_temperature',
        str(temperature),
    ])

  def get_night_light_temperature(self) -> int:
    output = (
        self.controller.adb.shell([
            'settings',
            'get',
            'secure',
            'night_display_color_temperature',
        ])
        .decode('utf-8')
        .strip()
    )

    try:
      return int(output)
    except ValueError:
      raise InfoNotFoundError(
          f'Failed to parse night_display_color_temperature: {output}'
      ) from None

  def _get_dumpsys_display_lines(self) -> list[str]:
    return (
        self.controller.adb.shell(['dumpsys', 'display']).decode().splitlines()
    )

  def _get_base_display_info_from_dumpsys_display(
      self, dumpsys_display_lines: list[str]
  ) -> list[str]:
    # example line:
    # mBaseDisplayInfo=DisplayInfo{"Built-in Screen", displayId 0...
    return [
        line for line in dumpsys_display_lines if 'mBaseDisplayInfo' in line
    ]

  def _get_display_ids_from_dumpsys_display(self) -> list[str]:
    """Returns the display IDs from dumpsys display."""

    display_ids = []
    dumpsys_display_lines = self._get_dumpsys_display_lines()

    # get display ids from base display info
    for (
        base_display_info_line
    ) in self._get_base_display_info_from_dumpsys_display(
        dumpsys_display_lines
    ):
      display_id = self._get_display_id_from_display_info_line(
          base_display_info_line
      )
      display_ids.append(display_id)

    return display_ids

  def _get_display_id_from_display_info_line(
      self, display_info_line: str
  ) -> str:
    match = re.search(r'displayId (\d+)', display_info_line)
    if match:
      return match.group(1)
    else:
      raise ValueError(
          'Failed to get display id from display info line:'
          f' {display_info_line}'
      )

  def _get_display_info_line(self, display_id: str = '') -> str:
    """Returns the display info line for the given display ID.

    Args:
      display_id: The display ID to get the info line for. If not specified, the
        info line for the built-in display will be returned.

    Returns:
      The display info line for the given display ID. Example line:
      mBaseDisplayInfo=DisplayInfo{"Built-in Screen", displayId 0, ...
    """
    dumpsys_display_lines = self._get_dumpsys_display_lines()
    display_info_lines = self._get_base_display_info_from_dumpsys_display(
        dumpsys_display_lines
    )
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
