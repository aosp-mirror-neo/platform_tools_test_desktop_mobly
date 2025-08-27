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

"""Interface for display operations for PASIT testing."""

import abc
from typing import Any


class BasePasitDisplay(metaclass=abc.ABCMeta):
  """Interface for display operations for PASIT testing."""

  class DisplayId(str):
    """Class for holding the display ID and additional information."""

    _id: str

    def __new__(cls, display_id: str):
      obj = str.__new__(cls, display_id)
      obj._id = display_id
      return obj

    @property
    def id(self) -> str:
      return self._id

    def __str__(self):
      return f'{self._id}'

    def __repr__(self):
      return f'{self._id}'

    def __hash__(self):
      return hash(self._id)

  class DisplayResolution:
    """Class for holding the resolution of a display."""

    def __init__(self, width: int, height: int):
      self.width = width
      self.height = height

    def __str__(self):
      return f'{self.width} x {self.height}'

    def __repr__(self):
      return f'{self.width} x {self.height}'

  class InfoNotFoundError(Exception):
    """Error raised when the display info is not found."""

  def __init__(self, controller: Any):
    """Initializes the PasitDisplay."""
    self.controller = controller

  @abc.abstractmethod
  def get_display_count(self) -> int:
    """Returns the number of connected displays."""
    raise NotImplementedError

  @abc.abstractmethod
  def get_display_ids(self) -> list[DisplayId]:
    """Returns the display IDs."""
    raise NotImplementedError

  @abc.abstractmethod
  def get_display_resolution(
      self, display_id: DisplayId | None = None
  ) -> DisplayResolution:
    """Returns the resolution of the display.

    Args:
      display_id: The display ID to get the resolution of. If not specified, the
        resolution of the first display will be returned.

    Returns:
      The resolution of the display.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def get_supported_display_resolutions(
      self, display_id: DisplayId | None = None
  ) -> dict[DisplayId, DisplayResolution]:
    """Returns the supported resolutions of the display.

    Args:
      display_id: The display ID to get the resolution of. If not specified, the
        resolution of the first display will be returned.

    Returns:
      A dictionary of supported resolutions of the display. The key is the
      ID for the resolution setting, and the value is the resolution.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def set_night_light_enabled(self, enabled: bool):
    """Enables or disables the night light.

    Args:
      enabled: True to enable the night light, False to disable it.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def get_night_light_enabled(self) -> bool:
    """Returns the night light enabled status.

    Returns:
      True if the night light is enabled, False otherwise.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def set_night_light_temperature(self, temperature: int):
    """Sets the night light temperature.

    Args:
      temperature: The night light temperature in Kelvin.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def get_night_light_temperature(self) -> int:
    """Returns the night light temperature.

    Returns:
      The night light temperature in Kelvin.
    """
    raise NotImplementedError
