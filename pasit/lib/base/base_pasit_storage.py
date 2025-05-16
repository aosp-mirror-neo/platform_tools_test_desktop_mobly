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

"""Interface for interacting with removable storage on a device."""

import abc
from typing import Any


class BasePasitStorage(metaclass=abc.ABCMeta):
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

  @abc.abstractmethod
  def format_external_storage(self) -> bool:
    """Formats the external storage device.

    Returns:
      True if the external storage device is formatted successfully, False
      otherwise.
    """
    raise NotImplementedError

  def __init__(self, controller: Any):
    """Initializes the PasitStorage class.

    Args:
      controller: The controller to use for accessing the device.
    """
    self.controller = controller
