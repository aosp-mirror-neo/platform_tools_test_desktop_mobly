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

"""Interface for file operations for PASIT testing."""

import abc
from typing import Any


class BasePasitFile(metaclass=abc.ABCMeta):
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

  @abc.abstractmethod
  def list_files(self, directory_path: str) -> list[str]:
    """Returns the list of file paths of the files in the directory.

    Args:
      directory_path: The path of the directory on the device to list.

    Returns:
      A list of file paths of the files in the directory.
    Raises:
      FileNotFoundError: If the directory does not exist.
    """
    raise NotImplementedError()

  @abc.abstractmethod
  def copy_file(self, file_path: str, dest_path: str):
    """Copies a file from one path to another on the device.

    Args:
      file_path: The path of the file on the device to copy.
      dest_path: The destination path on the device to copy the file to.
    """
    raise NotImplementedError()

  @abc.abstractmethod
  def remove_file(self, file_path: str):
    """Removes a file from the device.

    Args:
      file_path: The path of the file on the device to remove.
    """
    raise NotImplementedError()

  def __init__(self, controller: Any):
    self.controller = controller
