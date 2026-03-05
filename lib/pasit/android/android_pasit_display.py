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

import os
import typing

from lib.pasit.android import dumpsys_display_parser
from lib.pasit.android import dumpsys_surfaceflinger_parser
from lib.pasit.base import base_pasit_display
from mobly.controllers.android_device_lib import adb

DisplayId = base_pasit_display.BasePasitDisplay.DisplayId
DisplayResolution = base_pasit_display.BasePasitDisplay.DisplayResolution
InfoNotFoundError = base_pasit_display.BasePasitDisplay.InfoNotFoundError


class AndroidPasitDisplay(base_pasit_display.BasePasitDisplay):
  """PasitDisplay for Android devices."""

  def save_debug_info(self, output_path: str) -> None:
    with open(os.path.join(output_path, 'sys_class_drm_card.txt'), 'w') as f:
      dut_displays = self._write_command_with_output(
          f, 'ls -1d /sys/class/drm/card?-*'
      )
      for display in dut_displays.splitlines():
        drm_card_path = os.path.join(display.strip(), 'status')
        self._write_command_with_output(f, f'cat {drm_card_path}')

    self._save_command_output(output_path, 'modetest_output.txt', 'modetest')
    self._save_command_output(
        output_path, 'dumpsys_display.txt', 'dumpsys display'
    )
    self._save_command_output(
        output_path, 'dumpsys_surfaceflinger.txt', 'dumpsys SurfaceFlinger'
    )

  def _write_command_with_output(self, f: typing.TextIO, command: str) -> str:
    f.write(command)
    f.write('\n')
    output = self._safe_adb_shell(command)
    f.write(output)
    f.write('\n\n')
    return output

  def _save_command_output(
      self, output_path: str, file_name: str, command: str
  ) -> None:
    with open(os.path.join(output_path, file_name), 'w') as f:
      output = self._safe_adb_shell(command)
      f.write(output)

  def _safe_adb_shell(self, command: str) -> str:
    try:
      return self.controller.adb.shell(command).decode('utf-8')
    except adb.AdbError as e:
      return (
          f'command: {command} ret: {e.ret_code}\nstdout:'
          f' {e.stdout.decode("utf-8")}\nstderr: {e.stderr.decode("utf-8")}'
      )

  def get_display_ids(self) -> list[DisplayId]:
    return dumpsys_display_parser.DumpsysDisplayParser(
        self.controller
    ).get_display_ids()

  def get_internal_display_id(self) -> DisplayId:
    return dumpsys_display_parser.DumpsysDisplayParser(
        self.controller
    ).get_internal_display_id()

  def is_display_on(self, display_id: DisplayId | None = None) -> bool:
    return dumpsys_display_parser.DumpsysDisplayParser(
        self.controller
    ).is_display_on(display_id)

  def get_display_resolution(
      self, display_id: DisplayId | None = None
  ) -> tuple[str, DisplayResolution]:
    display_id = self._get_internal_display_id_if_empty(display_id)
    return dumpsys_surfaceflinger_parser.DumpsysSurfaceFlingerParser(
        self.controller
    ).get_display_resolution(display_id)

  def get_supported_display_resolutions(
      self, display_id: DisplayId | None = None
  ) -> dict[str, DisplayResolution]:
    display_id = self._get_internal_display_id_if_empty(display_id)
    return dumpsys_surfaceflinger_parser.DumpsysSurfaceFlingerParser(
        self.controller
    ).get_supported_display_resolutions(display_id)

  def set_display_resolution(
      self,
      display_mode_id: str,
      display_id: DisplayId | None = None,
  ):
    display_id = self._get_internal_display_id_if_empty(display_id)
    self.controller.adb.shell([
        'service',
        'call',
        'SurfaceFlinger',
        '1035',
        f'i32 {display_mode_id}',
        f'i64 {display_id.unique_id}',
    ])

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

  def _get_internal_display_id_if_empty(
      self, display_id: DisplayId | None = None
  ) -> DisplayId:
    if not display_id:
      return dumpsys_display_parser.DumpsysDisplayParser(
          self.controller
      ).get_internal_display_id()
    return display_id

  def set_mirror_mode(self, enabled: bool):
    self.controller.adb.shell([
        'settings',
        'put',
        'secure',
        'mirror_built_in_display',
        '1' if enabled else '0',
    ])

  def get_mirror_mode(self) -> bool:
    # mirror_built_in_display is 1 if mirror mode is enabled, 0 otherwise.
    return (
        self.controller.adb.shell([
            'settings',
            'get',
            'secure',
            'mirror_built_in_display',
        ])
        .decode('utf-8')
        .strip()
        .lower()
        .startswith('1')
    )
