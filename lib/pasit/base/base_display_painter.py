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

"""Base class for showing colors on device displays for testing."""

import abc
import logging
from typing import Any

from lib.utils import image


class BaseDisplayPainter(metaclass=abc.ABCMeta):
  """Base class for showing colors on device displays for testing."""

  class Error(Exception):
    """BaseDisplayPainter error."""

  def __init__(self, controller: Any):
    """Initializes the BaseDisplayPainter.

    Args:
      controller: The controller to use for displaying colors.
    """
    self.controller = controller

  def cleanup(self):
    """Cleans up after testing."""
    raise NotImplementedError

  @abc.abstractmethod
  def show_color_on_display(self, color: image.Color, display_id: str = ''):
    """Shows the given color on the display.

    Usage:
    Example 1: Show red color on default display.
      painter = self.create(display_painter)
      painter.show_color_on_display(image.Color(255, 0, 0, 255))

    Example 2: Show red color on all displays.
      display = self.create(pasit_display)
      display_ids = display.get_display_ids()
      for display_id in display_ids:
        painter.show_color_on_display(image.NamedColor.RED.value,
        display_id)

    Args:
      color: The color to show on the display.
      display_id: The display ID to show the color on. Display ID can be
        obtained from PasitDisplay via get_display_ids(). If empty, the color
        will be shown on the default display.

    Raises:
      Error: If the color was not successfully shown on the display.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def clean_color_on_display(self):
    """Cleans the color on the display.

    Raises:
      Error: If the color was not successfully cleaned on the display.
    """
    raise NotImplementedError

  def safe_clean_color_on_display(self):
    """Cleans the color on the display.

    Does not raise an error if the color was not successfully cleaned on the
    display.
    """
    try:
      self.clean_color_on_display()
    except Exception as e:
      logging.error('Failed to clean color on display %s', e)
