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

"""AndroidPasitStorage handles storage operations for PASIT testing on Android devices."""

from collections.abc import MutableSequence
import os

from mobly.controllers import android_device

from pasit.lib.base import base_pasit_storage


class AndroidMountInfo:
  """Represents information about an external storage mount."""

  def __init__(self, mount_line: str):
    [
        self.device_name,
        self.mount_point,
        self.fs_type,
        self.fs_options,
        _,
        _,
    ] = mount_line.split()


class AndroidPasitStorage(base_pasit_storage.BasePasitStorage):
  """PasitStorage for Android devices."""

  def _get_mount_infos(self) -> MutableSequence[AndroidMountInfo]:
    try:
      vold_mounts = self.controller.adb.shell('cat /proc/mounts | grep vold')
    except android_device.adb.AdbError:
      # the command can fail if the device is not mounted and grep returns
      # empty. Catch the error and return empty string as a mount point not
      # found.
      return []
    return [
        AndroidMountInfo(vold_mount)
        for vold_mount in vold_mounts.decode().splitlines()
    ]

  def get_external_mount_point(self) -> str:
    mount_infos = self._get_mount_infos()
    return mount_infos[0].mount_point if mount_infos else ''

  def eject_external_storage(self) -> bool:
    # Unmounts the storage as a temptorary solution.
    mount_infos = self._get_mount_infos()
    if not mount_infos:
      return False

    device_name = mount_infos[0].device_name
    self.controller.log.info(f'Unmounting external storage: {device_name}')
    volume = os.path.basename(device_name)
    self.controller.adb.shell(f'sm unmount {volume}')
    return True

  def format_external_storage(self) -> bool:
    path_prefix = '/dev/block/vold/public*'
    try:
      disk_paths = (
          self.controller.adb.shell(f'ls {path_prefix}').decode().splitlines()
      )
    except android_device.adb.AdbError:
      # the command can fail if no disk is found, return false as the device is
      # not formatted.
      return False
    if len(disk_paths) < 1:
      return False
    fmt_cmd = f'mkfs.exfat {path_prefix}/{disk_paths[0]} && sync'
    self.controller.log.info('Formatting external storage : %s.', fmt_cmd)
    self.controller.adb.shell(fmt_cmd)
    return True
