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

"""Provides Android-specific UI interaction tools for Mobly tests.

This module contains the AndroidUITools class, which implements the BaseUITools
interface to offer methods for launching, stopping, and waiting for common
Android applications using adb and UI Automator.
"""

import datetime
import logging
from typing import TypeAlias, Union

from lib.pasit.base import base_ui_tools
from mobly.controllers import android_device


BaseUIApplication: TypeAlias = base_ui_tools.BaseUITools.UIApplication
Error: TypeAlias = base_ui_tools.BaseUITools.Error


class AndroidUIApplication:
  """Represents a UI application on the device."""

  HID_SNIPPET = 'HID Snippet'
  COLOR_FILL_TEST_APP = 'Color Fill Test'


UIApplication: TypeAlias = Union[BaseUIApplication, AndroidUIApplication]


class AndroidUITools(base_ui_tools.BaseUITools[UIApplication]):
  """Manages UI interactions with standard Android applications on a device.

  This class uses a Mobly AndroidDevice controller to interact with apps
  like Settings, Files, and Camera. It provides methods to start, stop,
  and wait for these applications to open or close, primarily leveraging
  adb commands and the device's UI automator capabilities.

  Attributes:
    controller: The Mobly android_device.AndroidDevice instance to control.
  """

  _UI_APPLICATION_PACKAGE_NAME = {
      BaseUIApplication.SETTINGS: 'com.android.settings',
      BaseUIApplication.FILES: 'com.google.android.documentsui',
      BaseUIApplication.CAMERA: 'com.google.android.desktop.camera',
      AndroidUIApplication.HID_SNIPPET: 'com.google.android.hiddevicesnippet',
      AndroidUIApplication.COLOR_FILL_TEST_APP: (
          'com.google.android.colorfilltestapp'
      ),
  }

  # Required for maximize_app_window method.
  _UI_APPLICATION_LABEL = {
      AndroidUIApplication.HID_SNIPPET: 'androidx.multidex.MultiDexApplication',
      AndroidUIApplication.COLOR_FILL_TEST_APP: 'Color Fill Test',
  }

  def __init__(self, controller: android_device.AndroidDevice):
    self.controller = controller

  def launch_app(self, app: UIApplication) -> None:
    self._ensure_app_is_supported(app)
    self.controller.adb.shell([
        'monkey',
        '-p',
        self._UI_APPLICATION_PACKAGE_NAME[app],
        '-c',
        'android.intent.category.LAUNCHER',
        '1',
    ])

  def stop_app(self, app: UIApplication) -> None:
    self._ensure_app_is_supported(app)
    self.controller.adb.shell([
        'am',
        'force-stop',
        self._UI_APPLICATION_PACKAGE_NAME[app],
    ])

  def wait_app_open(self, app: UIApplication) -> bool:
    self._ensure_app_is_supported(app)
    try:
      return self.controller.ui(
          pkg=self._UI_APPLICATION_PACKAGE_NAME[app]
      ).wait.exists(
          timeout=datetime.timedelta(
              seconds=self._WAIT_APP_OPEN_TIMEOUT_SECONDS
          )
      )
    except Exception as e:  # pylint: disable=broad-except
      raise self.Error(f'Failed to wait for app to open: {app}') from e

  def wait_app_close(self, app: UIApplication) -> bool:
    self._ensure_app_is_supported(app)
    try:
      return self.controller.ui(
          pkg=self._UI_APPLICATION_PACKAGE_NAME[app]
      ).wait.gone(
          timeout=datetime.timedelta(
              seconds=self._WAIT_APP_CLOSE_TIMEOUT_SECONDS
          )
      )
    except Exception as e:  # pylint: disable=broad-except
      raise self.Error(f'Failed to wait for app to close: {app}') from e

  def maximize_app_window(self, app: UIApplication) -> bool:
    self._ensure_app_has_label(app)
    button = self.controller.ui(
        res='com.android.systemui:id/maximize_window',
        pkg='com.android.systemui',
        descContains=self._UI_APPLICATION_LABEL[app],
    )

    if not button.wait.exists(timeout=datetime.timedelta(seconds=5)):
      logging.warning(
          'Maximize button not found for the window, skipping window'
          ' maximization.'
      )
      self.controller.ui.dump()
      return False

    button_text = button.description
    if 'Restore' in button_text:
      logging.debug('Window is already maximized.')
      return True
    elif 'Max' in button_text:
      return button.click()
    else:
      logging.warning(
          'Maximize button has unexpected text: %s. Skipping window'
          ' maximization.',
          button_text,
      )
      return False

  def is_app_installed(self, app: UIApplication) -> bool:
    self._ensure_app_is_supported(app)
    package_name = self._UI_APPLICATION_PACKAGE_NAME[app]
    output = self.controller.adb.shell([
        'pm',
        'list',
        'packages',
        package_name,
    ])
    return package_name in output.decode('utf-8')

  def get_window_count(self, app: UIApplication) -> int:
    self._ensure_app_is_supported(app)
    try:
      # Use the standard Android content view resource ID to count app
      # windows. This is more reliable than counting all UI elements with the
      # package name, which can include child views and lead to overcounting.
      # This approach works for both desktop (windowed) and fullscreen
      # instances.
      return self.controller.ui(
          pkg=self._UI_APPLICATION_PACKAGE_NAME[app],
          resourceId='android:id/content',
      ).count
    except Exception as e:  # pylint: disable=broad-except
      raise self.Error('Failed to get app window count') from e

  def get_app_package_name(self, app: UIApplication) -> str:
    """Returns the package name of the UI application.

    Available only on Android.

    Args:
      app: The UI application to get the package name for.

    Returns:
      The package name of the UI application.
    Raises:
      ValueError: If the UI application is not supported.
    """
    self._ensure_app_is_supported(app)
    return self._UI_APPLICATION_PACKAGE_NAME[app]

  def _ensure_app_is_supported(self, app: UIApplication) -> None:
    if app not in self._UI_APPLICATION_PACKAGE_NAME:
      raise ValueError(
          f'Unsupported UI application: {app}. Supported applications:'
          f' {self._UI_APPLICATION_PACKAGE_NAME.keys()}'
      )

  def _ensure_app_has_label(self, app: UIApplication) -> None:
    if app not in self._UI_APPLICATION_LABEL:
      raise ValueError(
          f'Unsupported UI application: {app}. Supported applications:'
          f' {self._UI_APPLICATION_LABEL.keys()}'
      )
