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

"""Provides utilities for installing and uninstalling APKs on Android devices."""

import os
import sys

from mobly.controllers import android_device
from mobly.controllers.android_device_lib import apk_utils
from mobly.controllers.android_device_lib import snippet_client_v2
from snippet_uiautomator import uiautomator


class ApkTools:
  """Provides utilities for installing and uninstalling APKs on Android devices.

  Installs and uninstalls mobly bundled snippets and UI Automator APKs on
  Android devices.
  """

  # snippet apk is in same directory as this mobly executable
  BASE_APK_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))
  SNIPPET_APK_PATH = os.path.join(BASE_APK_PATH, 'mobly-bundled-snippets.apk')
  UIAUTOMATOR_APK_PATH = os.path.join(BASE_APK_PATH, 'snippet-uiautomator.apk')

  def __init__(self, controller: android_device.AndroidDevice):
    self.controller = controller
    # uninstall apks to avoid INSTALL_FAILED_UPDATE_INCOMPATIBLE errors
    self.uninstall_all()

  def install_all(self, user_id: int):
    self.install_mbs(user_id)
    self._load_mbs(user_id)
    self._register_uiautomator()

  def install_mbs(self, user_id: int):
    """Installs Mobly Bundled Snippets."""
    apk_utils.install(
        self.controller,
        self.SNIPPET_APK_PATH,
        user_id,
    )

  def uninstall_all(self):
    apk_utils.uninstall(self.controller, android_device.MBS_PACKAGE)
    apk_utils.uninstall(self.controller, uiautomator.UIAUTOMATOR_PACKAGE_NAME)

  def _register_uiautomator(self):
    """Installs UI Automator."""
    snippet = uiautomator.Snippet()
    snippet.file_path = str(self.UIAUTOMATOR_APK_PATH)
    self.controller.services.register(
        uiautomator.ANDROID_SERVICE_NAME,
        uiautomator.UiAutomatorService,
        configs=uiautomator.UiAutomatorConfigs(snippet=snippet),
    )

  def _load_mbs(self, user_id: int):
    self.controller.load_snippet(
        'mbs',
        android_device.MBS_PACKAGE,
        config=snippet_client_v2.Config(user_id),
    )
