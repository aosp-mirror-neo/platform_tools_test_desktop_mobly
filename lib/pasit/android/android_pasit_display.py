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


from lib.pasit.android import dumpsys_display_parser
from lib.pasit.base import base_pasit_display

DisplayId = base_pasit_display.BasePasitDisplay.DisplayId
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

  def get_display_ids(self) -> list[DisplayId]:
    return dumpsys_display_parser.DumpsysDisplayParser(
        self.controller
    ).get_display_ids()

  def get_display_resolution(
      self, display_id: DisplayId | None = None
  ) -> DisplayResolution:
    return dumpsys_display_parser.DumpsysDisplayParser(
        self.controller
    ).get_display_resolution(display_id)

  def get_supported_display_resolutions(
      self, display_id: DisplayId | None = None
  ) -> dict[str, DisplayResolution]:
    return dumpsys_display_parser.DumpsysDisplayParser(
        self.controller
    ).get_supported_display_resolutions(display_id)

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
