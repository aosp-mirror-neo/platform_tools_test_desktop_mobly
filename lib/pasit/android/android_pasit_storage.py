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

from lib.pasit.base import base_pasit_storage


class SmVolumeInfo:
  """Represents information about a storage manager volume."""

  def __init__(self, volume_info: str):
    [
        self._volume_id,
        self._state,
        self._fsid,
    ] = volume_info.split()

  @property
  def volume_id(self) -> str:
    return self._volume_id

  @property
  def mounted(self) -> bool:
    return self._state == 'mounted'

  @property
  def mount_point(self) -> str:
    if self._fsid != 'null':
      return os.path.join('/mnt', 'media_rw', self._fsid)
    return ''

  @property
  def fsid(self) -> str:
    return self._fsid


class AndroidPasitStorage(base_pasit_storage.BasePasitStorage):
  """PasitStorage for Android devices."""

  def _get_volume_info(self) -> MutableSequence[SmVolumeInfo]:
    volumes = self.controller.adb.shell(['sm', 'list-volumes', 'public'])
    return [
        SmVolumeInfo(vold_mount) for vold_mount in volumes.decode().splitlines()
    ]

  def get_external_storage_blkdevs(self) -> MutableSequence[str]:
    disks = self.controller.adb.shell(['sm', 'list-disks'])
    return disks.decode().splitlines()

  def get_external_mount_point(self) -> str:
    volumes = self._get_volume_info()
    if not volumes or not volumes[0].mounted:
      return ''
    return volumes[0].mount_point

  def eject_external_storage(self) -> bool:
    # Unmounts the storage as a temptorary solution.
    volumes = self._get_volume_info()
    if not volumes or not volumes[0].mounted:
      return False
    volume = volumes[0]
    self.controller.log.info(f'Unmounting external storage: {volume.volume_id}')
    self.controller.adb.shell(['sm', 'unmount', volume.volume_id])
    return True

  def format_external_storage(self) -> bool:
    disks = self.get_external_storage_blkdevs()
    if len(disks) != 1:
      self.controller.log.error(
          'Expected exactly one disk, got %d: %s.', len(disks), disks
      )
      return False
    disk = disks[0]
    self.controller.log.info(
        'Formatting external storage: %s.', disk
    )
    self.controller.adb.shell(['sm', 'partition', disk, 'public', '100'])
    return True
