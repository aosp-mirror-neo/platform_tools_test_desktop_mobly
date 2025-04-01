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

"""PasitFileInterface handles file operations for PASIT testing."""

import abc
from typing import Any

from pasit.lib import pasit_device


class PasitFileInterface(metaclass=abc.ABCMeta):
  """Interface for file operations for PASIT testing."""

  @abc.abstractmethod
  def push_file(self, file_path: str, dest_path: str):
    """Copies a file on the host to the device.

    This will overwrite the file if it exists at the destination path.

    Args:
      file_path: The path of the file on the host to push.
      dest_path: The destination path on the device to push the file to.
    """
    raise NotImplementedError()

  @abc.abstractmethod
  def pull_file(self, file_path: str, dest_path: str):
    """Copies a file from the device to the host.

    This will overwrite the file if it exists at the destination path.

    Args:
      file_path: The path of the file on the device to pull.
      dest_path: The destination path on the host to pull the file to.
    """
    raise NotImplementedError()

  def __init__(self, controller: Any):
    self.controller = controller


class AndroidPasitFileInterface(PasitFileInterface):
  """PasitFileInterface for Android devices."""

  def push_file(self, file_path: str, dest_path: str):
    self.controller.adb.push([file_path, dest_path])

  def pull_file(self, file_path: str, dest_path: str):
    self.controller.adb.pull([file_path, dest_path])


def create(device: pasit_device.PasitDevice) -> PasitFileInterface:
  """Creates a PasitFileInterface for the given controller."""
  if device.is_android_device():
    return AndroidPasitFileInterface(device.controller)
  raise ValueError(f'Unsupported controller type: {type(device.controller)}')
