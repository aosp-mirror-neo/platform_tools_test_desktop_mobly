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

"""Utilities for installing and uninstalling snippets on Android devices."""

import os
import sys

from mobly.controllers import android_device
from mobly.controllers.android_device_lib import apk_utils
from mobly.controllers.android_device_lib import snippet_client_v2
from snippet_uiautomator import uiautomator


class SnippetTools:
  """Utilities for installing and uninstalling snippets on Android devices.

  Installs and uninstalls mobly bundled snippets and UI Automator APKs on
  Android devices.
  """

  # snippet apk is in same directory as this mobly executable
  SNIPPET_APK_PATH = os.path.join(
      os.path.dirname(os.path.abspath(sys.argv[0])),
      'mobly-bundled-snippets.apk',
  )
  UIAUTOMATOR_APK_PATH = os.path.join(
      os.path.dirname(os.path.abspath(sys.argv[0])),
      'snippet-uiautomator.apk',
  )

  def __init__(self, controller: android_device.AndroidDevice):
    self.controller = controller

  def install_and_load_mbs(self, user_id: int):
    """Installs all required snippets."""
    self.install_mbs(user_id)
    self._load_mbs(user_id)

  def install_mbs(self, user_id: int):
    """Installs Mobly Bundled Snippets."""
    apk_utils.install(
        device=self.controller,
        apk_path=self.SNIPPET_APK_PATH,
        timeout=10,
        user_id=user_id,
    )

  def uninstall_all(self):
    """Uninstalls all snippets installed with SnippetTools."""
    apk_utils.uninstall(self.controller, android_device.MBS_PACKAGE)
    apk_utils.uninstall(self.controller, uiautomator.UIAUTOMATOR_PACKAGE_NAME)

  def register_uiautomator(self):
    """Registers UI Automator service."""
    snippet = uiautomator.Snippet()
    snippet.file_path = str(self.UIAUTOMATOR_APK_PATH)
    self.controller.services.register(
        uiautomator.ANDROID_SERVICE_NAME,
        uiautomator.UiAutomatorService,
        configs=uiautomator.UiAutomatorConfigs(snippet=snippet),
    )

  def reinstall_uiautomator(self):
    """Reinstalls UI Automator APK without reregistering the service."""
    apk_utils.install(
        device=self.controller,
        apk_path=self.UIAUTOMATOR_APK_PATH,
        timeout=10,
    )

  def _load_mbs(self, user_id: int):
    self.controller.load_snippet(
        'mbs',
        android_device.MBS_PACKAGE,
        config=snippet_client_v2.Config(user_id=user_id),
    )
