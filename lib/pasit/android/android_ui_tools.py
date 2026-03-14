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
from typing import TypeAlias

from lib.pasit.base import base_ui_tools
from mobly.controllers import android_device


UIApplication: TypeAlias = base_ui_tools.BaseUITools.UIApplication
Error: TypeAlias = base_ui_tools.BaseUITools.Error


class AndroidUITools(base_ui_tools.BaseUITools):
  """Manages UI interactions with standard Android applications on a device.

  This class uses a Mobly AndroidDevice controller to interact with apps
  like Settings, Files, and Camera. It provides methods to start, stop,
  and wait for these applications to open or close, primarily leveraging
  adb commands and the device's UI automator capabilities.

  Attributes:
    controller: The Mobly android_device.AndroidDevice instance to control.
  """

  _UI_APPLICATION_PACKAGE_NAME = {
      UIApplication.SETTINGS: 'com.android.settings',
      UIApplication.FILES: 'com.google.android.documentsui',
      UIApplication.CAMERA: 'com.google.android.desktop.camera',
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

  def _ensure_app_is_supported(self, app: UIApplication) -> None:
    if app not in self._UI_APPLICATION_PACKAGE_NAME:
      raise ValueError(
          f'Unsupported UI application: {app}. Supported applications:'
          f' {self._UI_APPLICATION_PACKAGE_NAME.keys()}'
      )
