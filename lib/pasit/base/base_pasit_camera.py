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

"""Interface for camera operations for PASIT testing."""

import abc
from collections.abc import MutableSequence
import enum
from typing import Any


class BasePasitCamera(metaclass=abc.ABCMeta):
  """Interface for camera operations for PASIT testing."""

  class Error(Exception):
    """BasePasitCamera error."""

  class Mode(enum.Enum):
    """The capture mode for the camera app."""

    VIDEO = 'video'
    PHOTO = 'photo'

  def __init__(self, controller: Any):
    """Initializes the PasitCamera."""
    self.controller = controller

  @abc.abstractmethod
  def launch_camera_app(self, mode: Mode = Mode.PHOTO) -> bool:
    """Launches the camera app.

    Args:
      mode: The capture mode to launch the camera app in.

    Returns:
      True if the camera app was launched successfully, False otherwise.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def close_camera_app(self):
    """Closes the camera app."""
    raise NotImplementedError

  @abc.abstractmethod
  def get_connected_cameras(self) -> MutableSequence[str]:
    """Finds the connected camera devices."""
    raise NotImplementedError

  @abc.abstractmethod
  def is_camera_app_using_camera(self, camera_device: str) -> bool:
    """Checks if the camera app is using the camera_device."""
    raise NotImplementedError

  @abc.abstractmethod
  def switch_camera(self):
    """Switches to the front or back camera."""
    raise NotImplementedError

  @abc.abstractmethod
  def switch_mode(self, mode: Mode) -> bool:
    """Switches to the specified mode.

    Args:
      mode: The capture mode to switch to.

    Returns:
      True if the mode was switched successfully, False otherwise.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def take_photo(self):
    """Captures a photo."""
    raise NotImplementedError

  @abc.abstractmethod
  def start_recording_video(self):
    """Starts recording a video."""
    raise NotImplementedError

  @abc.abstractmethod
  def stop_recording_video(self):
    """Stops recording a video."""
    raise NotImplementedError

  @abc.abstractmethod
  def get_files_path(self) -> str:
    """Returns the path of the captured photos and videos directory."""
    raise NotImplementedError

  @abc.abstractmethod
  def maximize_camera_app_window(self):
    """Maximizes the camera app window."""
    raise NotImplementedError
