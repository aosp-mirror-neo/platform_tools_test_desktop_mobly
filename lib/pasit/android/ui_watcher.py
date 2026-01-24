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

"""UI watcher for PASIT."""

import logging
from mobly.controllers import android_device


class UIWatcherParams:
  """UI watcher parameters."""

  def __init__(
      self,
      text_to_match: str,
      text_to_click: str,
  ):
    self.watcher_name = f"watcher_{text_to_match.replace(' ', '_').lower()}"
    self.text_to_match = text_to_match
    self.text_to_click = text_to_click


class UIWatcher:
  """UI watcher for PASIT."""

  def __init__(self, controller: android_device.AndroidDevice):
    self.controller = controller
    self.watchers = []

  def add(self, params: UIWatcherParams) -> bool:
    """Adds a watcher to close a window.

    Checks if the window exists and if so closes it. Also adds a watcher to
    close the window if it appears again during the test. This is to prevent the
    window from obscuring the view of UI elements.

    Args:
      params: The UI watcher parameters.

    Returns:
      True if the window was detected and closed, False otherwise.
    """
    window_detected = False
    try:
      if self.controller.ui(text=params.text_to_match).exists:
        self.controller.ui(text=params.text_to_click).click()
        logging.warning(
            "'%s' window detected and closed.", params.text_to_match
        )
        window_detected = True

      self.controller.ui.watcher(params.watcher_name).when(
          text=params.text_to_match
      ).click(text=params.text_to_click)
      self.watchers.append(params.watcher_name)
    except Exception as e:  # pylint: disable=broad-except
      logging.error(
          "Failed to add watcher for '%s' window: %s",
          params.text_to_match,
          e,
      )
    return window_detected

  def remove_all(self) -> None:
    """Removes all watchers."""
    for watcher in self.watchers:
      self.remove(watcher)

  def remove(self, watcher_name: str) -> None:
    """Removes the watcher.

    Args:
      watcher_name: The name of the watcher.

    Logs if the watcher was triggered and closed the window.
    """
    try:
      if self.controller.ui.watcher(watcher_name).triggered:
        logging.warning(
            "Watcher %s triggered and closed the window.", watcher_name
        )
      self.controller.ui.watcher(watcher_name).remove()
    except Exception as e:  # pylint: disable=broad-except
      logging.error(
          "Failed to remove watcher %s: %s",
          watcher_name,
          e,
      )
