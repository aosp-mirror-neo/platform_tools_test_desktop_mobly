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

"""Interface for HID operations for PASIT testing."""

import abc
import dataclasses
from typing import Any, List


class BasePasitHID(metaclass=abc.ABCMeta):
  """Interface for HID operations for PASIT testing."""

  @dataclasses.dataclass
  class DeviceInfo:
    """Represents information about an HID device."""

    name: str
    vendor_id: int
    product_id: int
    type: str  # e.g., "Keyboard", "Mouse", "Keyboard & Mouse"

  def __init__(self, controller: Any):
    """Initializes the PasitHID."""
    self.controller = controller

  @abc.abstractmethod
  def cleanup(self) -> None:
    """Cleans up after testing."""
    raise NotImplementedError

  @abc.abstractmethod
  def get_hid_devices(self) -> List[DeviceInfo]:
    """Returns a list of connected HID devices."""
    raise NotImplementedError
