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

"""PasitDevice handles the setup of a device for PASIT testing."""

import abc
from typing import Any, Iterable


class BasePasitDevice(metaclass=abc.ABCMeta):
  """Base class for PASIT device."""

  controller: Any

  def __init__(self, controller: Any):
    """Initializes the PasitDevice.

    Args:
      controller: The controller to use for the PASIT device.
    """
    self.controller = controller

  @abc.abstractmethod
  def shell(self, params: Iterable[str]):
    """Sends the given parameters to the console."""
    raise NotImplementedError

  @abc.abstractmethod
  def reboot(self):
    """Reboots the device."""
    raise NotImplementedError
