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
    _human_readable_id: str

    def __new__(
        cls, display_id: str, human_readable_id: str = ''
    ) -> 'DisplayId':
      obj = str.__new__(cls, display_id)
      obj._id = display_id
      obj._human_readable_id = human_readable_id
      return obj

    @property
    def id(self) -> str:
      return self._id

    @property
    def human_readable_id(self) -> str:
      return self._human_readable_id

    def __str__(self):
      # __str__ may be used by legacy code which expected display_id to be a
      # string so do not modify this without considering the impact on legacy
      # code.
      return f'{self._id}'

    def __repr__(self):
      if self._human_readable_id:
        return f'{self._human_readable_id} [ID={self._id}]'
      return f'[ID={self._id}]'

    def __hash__(self):
      return hash(self._id)

    def is_same_physical_display(self, other: 'DisplayId') -> bool:
      """Checks if two display IDs represent the same physical display.

      Numerical display IDs (e.g., ID 0, ID 16) are not always stable on
      Android. For example, when a laptop lid is closed, the framework may
      re-assign the primary ID (0) to an external monitor and assign a new ID to
      the internal panel. This method allows the test to track the physical
      display across such re-assignment events by prioritizing stable
      identifiers like UIDs.

      Args:
        other: The other display ID to compare.

      Returns:
        True if the two display IDs represent the same physical display.
      """
      # First check for exact equality (ID + UID + Human Readable).
      if self == other:
        return True

      # If human readable IDs are the same then assume they are the same
      # physical display.
      return (
          self.human_readable_id
          and self.human_readable_id == other.human_readable_id
      )

  class DisplayResolution:
    """Class for holding the resolution of a display."""

    def __init__(self, width: int, height: int):
      self.width = width
      self.height = height

    def __str__(self):
      return f'{self.width} x {self.height}'

    def __repr__(self):
      return f'{self.width} x {self.height}'

    def __eq__(self, other):
      return self.width == other.width and self.height == other.height

  class InfoNotFoundError(Exception):
    """Error raised when the display info is not found."""

  def __init__(self, controller: Any):
    """Initializes the PasitDisplay."""
    self.controller = controller

  @abc.abstractmethod
  def save_debug_info(self, output_path: str):
    """Saves the debug info of the display."""
    raise NotImplementedError

  @abc.abstractmethod
  def get_display_ids(self) -> list[DisplayId]:
    """Returns the display IDs."""
    raise NotImplementedError

  @abc.abstractmethod
  def get_internal_display_id(self) -> DisplayId:
    """Returns the internal display ID."""
    raise NotImplementedError

  @abc.abstractmethod
  def is_display_on(self, display_id: DisplayId | None = None) -> bool:
    """Returns True if the display is ON, False otherwise.

    Args:
      display_id: The display ID to get the state of. If not specified, the
        state of the internal display will be checked.

    Returns:
      True if the display is ON, False otherwise.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def get_display_resolution(
      self, display_id: DisplayId | None = None
  ) -> tuple[str, DisplayResolution]:
    """Returns the resolution of the display.

    Args:
      display_id: The display ID to get the resolution of. If not specified, the
        resolution of the first display will be returned.

    Returns:
      A tuple of (display_mode_id, resolution). The display_mode_id is the ID
      for the resolution setting, and the resolution is the resolution of the
      display.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def get_supported_display_resolutions(
      self, display_id: DisplayId | None = None
  ) -> dict[str, DisplayResolution]:
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
  def set_display_resolution(
      self,
      display_mode_id: str,
      display_id: DisplayId | None = None,
  ):
    """Sets the resolution of the display.

    Args:
      display_mode_id: The ID for the resolution setting.
      display_id: The display ID to set the resolution of. If not specified, the
        resolution of the internal display will be set.
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

  @abc.abstractmethod
  def set_mirror_mode(self, enabled: bool):
    """Enables or disables the mirror mode.

    Args:
      enabled: True to enable the mirror mode, False to disable it.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def get_mirror_mode(self) -> bool:
    """Returns the mirror mode enabled status.

    Returns:
      True if the mirror mode is enabled, False otherwise.
    """
    raise NotImplementedError
