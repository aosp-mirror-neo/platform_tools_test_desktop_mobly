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

"""PasitDevice handles the setup of a device for PASIT testing."""

import abc
import os
import sys
from typing import Any, Iterable

from mobly import base_test
from mobly.controllers import android_device
from mobly.controllers.android_device_lib import adb
from mobly.controllers.android_device_lib import apk_utils
from mobly.controllers.android_device_lib import snippet_client_v2

ANDROID_DEVICE_TYPE = 'AndroidDevice'

AdbError = android_device.adb.AdbError


class PasitDevice(metaclass=abc.ABCMeta):
  """Base class for PASIT device."""

  controller: Any

  def __init__(self, controller: Any):
    """Initializes the PasitDevice.

    Args:
      controller: The controller to use for the PASIT device.
    """
    self.controller = controller

  def is_android_device(self) -> bool:
    """Returns true if the device is an Android device."""
    return isinstance(self.controller, android_device.AndroidDevice)

  @abc.abstractmethod
  def shell(self, params: Iterable[str]):
    """Sends the given parameters to the console."""
    raise NotImplementedError

  @abc.abstractmethod
  def reboot(self):
    """Reboots the device."""
    raise NotImplementedError


class AndroidPasitDevice(PasitDevice):
  """AndroidPasitDevice handles the setup of an Android device for PASIT testing."""

  FOUR_CORNER_EXIT_ACTION_ERROR = (
      'Activity not started, unable to resolve Intent'
  )
  LOGGED_IN_USER_ID = 10
  LOGIN_SCREEN_USER_ID = 0

  # snippet apk is in same directory as this mobly executable
  SNIPPET_APK_PATH = os.path.join(
      os.path.dirname(os.path.abspath(sys.argv[0])),
      'mobly-bundled-snippets.apk',
  )

  def __init__(self, controller: Any):
    super().__init__(controller)
    # Install Mobly Bundled Snippets.
    apk_utils.install(
        self.controller,
        self.SNIPPET_APK_PATH,
        user_id=self.LOGIN_SCREEN_USER_ID,
    )

    self.controller.load_snippet(
        'mbs',
        android_device.MBS_PACKAGE,
        config=snippet_client_v2.Config(user_id=self.LOGIN_SCREEN_USER_ID),
    )

    self.controller.root_adb()
    # Skip OOBE/Setup Wizard - go/skip-oobe
    try:
      self.controller.adb.shell(
          ['am', 'start', '-a', 'com.android.setupwizard.FOUR_CORNER_EXIT']
      )
    except adb.AdbError as e:
      if self.FOUR_CORNER_EXIT_ACTION_ERROR in str(e.stderr):
        # The four corner exit action will not run if the device is already
        # logged in or if the device is not rooted.
        self.controller.log.info('Ignoring failure to skip OOBE/Setup Wizard.')
        self.controller.log.info(e)
      else:
        raise e

    # Bypass the login screen.
    self._switch_user(self.LOGGED_IN_USER_ID)

  def shell(self, params: Iterable[str]):
    self.controller.adb.shell(params)

  def reboot(self):
    self.controller.reboot()
    self._switch_user(self.LOGGED_IN_USER_ID)

  def _switch_user(self, user_id: int):
    """Switches the user on the device."""
    self.controller.adb.shell(['am', 'switch-user', str(user_id)])


def is_android_device(test_class: base_test.BaseTestClass) -> bool:
  """Returns true if the test class is an Android device."""
  return ANDROID_DEVICE_TYPE in test_class.controller_configs


def create(test_class: base_test.BaseTestClass) -> PasitDevice:
  """Creates a PasitDevice for the given controller."""
  if is_android_device(test_class):
    controller = test_class.register_controller(android_device)[0]
    return AndroidPasitDevice(controller)
  else:
    raise ValueError(
        'No device type found for controller config:'
        f' {test_class.controller_configs}'
    )
