# Copyright 2026 Google LLC
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

"""Defines the abstract base class for device UI interaction tools.

This module provides the BaseUITools class, an abstract base class (ABC)
that defines the common interface for interacting with device UI applications
such as Settings, Files, and Camera. Concrete implementations should
inherit from this class and implement the abstract methods.
"""

import abc
import enum
from typing import Generic, TypeVar


UIApplicationType = TypeVar('UIApplicationType', bound=enum.Enum)


class BaseUITools(abc.ABC, Generic[UIApplicationType]):
  """Abstract base class for device UI interaction tools.

  This class defines the standard methods for launching, stopping, and
  waiting for UI applications on a device. Subclasses must implement
  the abstract methods to provide platform-specific functionality.

  Attributes:
    UIApplication: An enum representing the supported UI applications.
    Error: Base exception class for errors raised by UI tools.
  """

  _WAIT_APP_OPEN_TIMEOUT_SECONDS = 10
  _WAIT_APP_CLOSE_TIMEOUT_SECONDS = 10

  class UIApplication(enum.Enum):
    """Represents a UI application on the device."""

    SETTINGS = 'Settings'
    FILES = 'Files'
    CAMERA = 'Camera'

  class Error(Exception):
    """Base exception for UI tool operations."""

  @abc.abstractmethod
  def launch_app(self, app: UIApplicationType) -> None:
    """Launches the UI application on the device.

    Args:
      app: The UI application to launch.

    Raises:
      ValueError: If the UI application is not supported.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def stop_app(self, app: UIApplicationType) -> None:
    """Stops the UI application on the device.

    Args:
      app: The UI application to stop.

    Raises:
      ValueError: If the UI application is not supported.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def wait_app_open(self, app: UIApplicationType) -> bool:
    """Waits for the UI application to appear.

    Waits for 10 seconds for the UI application to appear.

    Args:
      app: The UI application to wait for.

    Returns:
      True if the UI application appeared, False otherwise.

    Raises:
      ValueError: If the UI application is not supported.
      Error: If the UI application fails to appear.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def wait_app_close(self, app: UIApplicationType) -> bool:
    """Wait for the UI application to close.

    Waits for 10 seconds for the UI application to close.

    Args:
      app: The UI application to wait for.

    Returns:
      True if the UI application closed, False otherwise.

    Raises:
      ValueError: If the UI application is not supported.
      Error: If the UI application fails to close.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def maximize_app_window(self, app: UIApplicationType) -> bool:
    """Maximize the UI application window.

    Args:
      app: The UI application to maximize the window for.

    Returns:
      True if the UI application window was maximized, False otherwise.

    Raises:
      ValueError: If the UI application is not supported.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def is_app_installed(self, app: UIApplicationType) -> bool:
    """Checks if the UI application is installed.

    Args:
      app: The UI application to check if installed.

    Returns:
      True if the UI application is installed, False otherwise.

    Raises:
      ValueError: If the UI application is not supported.
    """
    raise NotImplementedError

  def get_window_count(self, app: UIApplicationType) -> int:
    """Returns the number of UI application windows.

    Args:
      app: The UI application to get the window count for.

    Returns:
      The number of UI application windows.
    Raises:
      ValueError: If the UI application is not supported.
      Error: If the UI application window count cannot be determined.
    """
    raise NotImplementedError
