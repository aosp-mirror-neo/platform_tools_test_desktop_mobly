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

"""PasitExternalStorageInfo handles functionality related to device storage for PASIT testing."""

import abc
from collections.abc import MutableSequence
import os
import time
from typing import Any, Dict

from pasit.lib import pasit_device


class PasitExternalStorageInfo(metaclass=abc.ABCMeta):
  """Interface for interacting with removable storage on a device."""

  @abc.abstractmethod
  def get_external_mount_point(self) -> str:
    """Gets the external removable storage mount point.

    Returns:
      The external removable storage mount point if exists, empty string
      otherwise.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def eject_external_storage(self) -> bool:
    """Ejects the external removable storage.

    Fails if the external storage is not mounted at the beginning.

    Returns:
      True if the external storage device is ejected successfully, False
      otherwise.
    """
    raise NotImplementedError

  def wait_for_external_mount_point(self, timeout: int = 20) -> str:
    """Blocks until an external removable storage mount point is found.

    Args:
      timeout: The number of seconds to wait for the removable storage to mount;
        default is 20 seconds.

    Returns:
      A path for the external removable storage.

    Raises:
      TimeoutError: If the removable storage mount point is not detected within
        the timeout.
    """
    start_time = time.time()
    while not self.get_external_mount_point():
      if time.time() - start_time > timeout:
        raise TimeoutError(
            'Timed out waiting for removable storage to mount. Waited for'
            f' {timeout} seconds.'
        )
      time.sleep(1)

    return self.get_external_mount_point()

  @abc.abstractmethod
  def format_external_storage(self) -> bool:
    """Formats the external storage device.

    Returns:
      True if the external storage device is formatted successfully, False
      otherwise.
    """
    raise NotImplementedError

  def __init__(self, controller: Any):
    """Initializes the PasitExternalStorageInfo class.

    Args:
      controller: The controller to use for accessing the device.
    """
    self.controller = controller


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


class AndroidPasitExternalStorageInfo(PasitExternalStorageInfo):
  """PasitExternalStorageInfo for Android devices."""

  def _get_mount_infos(self) -> MutableSequence[AndroidMountInfo]:
    try:
      vold_mounts = self.controller.adb.shell('cat /proc/mounts | grep vold')
    except pasit_device.AdbError:
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
    path_prefix = '/dev/block/vold'
    disk_paths = (
        self.controller.adb.shell(f'ls {path_prefix}').decode().splitlines()
    )
    if len(disk_paths) < 1:
      return False
    fmt_cmd = f'mkfs.exfat {path_prefix}/{disk_paths[0]} && sync'
    self.controller.log.info('Formatting external storage : %s.', fmt_cmd)
    self.controller.adb.shell(fmt_cmd)
    return True


def create(device: pasit_device.PasitDevice) -> PasitExternalStorageInfo:
  """Creates a PasitExternalStorageInfo object for the given controller."""
  if device.is_android_device():
    return AndroidPasitExternalStorageInfo(device.controller)
  else:
    raise ValueError(f'{device.controller} is not supported.')
