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


"""AndroidUserTools provides tools for managing user sessions on an Android device."""

import logging

from lib.pasit.base import base_user_tools
from lib.utils import retry
from mobly.controllers import android_device
from mobly.controllers.android_device_lib import adb

LOGGED_IN_USER_ID = 10
LOGIN_SCREEN_USER_ID = 0

DETECT_LAUNCHER_AS_ACTIVE_PACKAGE_RETRY_POLICY = retry.RetryPolicy(
    max_tries=10, delay_seconds=1
)


class UserSessionError(Exception):
  """Raised when there is an error managing user sessions on an Android device."""


class UnexpectedActivePackageError(Exception):
  """Error when the active package is not the expected package."""

  def __init__(self, expected_package: str, actual_package: str):
    super().__init__(
        f'Expected package {expected_package} to be active, but'
        f' {actual_package} is active.'
    )
    self.expected_package = expected_package
    self.actual_package = actual_package


class AndroidUserTools(base_user_tools.BaseUserTools):
  """AndroidUserTools provides tools for managing user sessions on an Android device."""

  _IGNORABLE_OOBE_ERRORS = (
      'Activity not started, unable to resolve Intent',
      'Activity not started, not allowed for the given user',
  )
  _LOGIN_SCREEN_PACKAGE_NAME = 'com.google.android.desktop.identity.login'
  _LAUNCHER_PACKAGE_NAME = 'com.google.android.apps.nexuslauncher'

  def __init__(self, controller: android_device.AndroidDevice):
    self.controller = controller

  def skip_oobe(self) -> None:
    """Skips the OOBE flow."""
    # Skip OOBE/Setup Wizard - go/skip-oobe
    try:
      self.controller.adb.shell(
          ['am', 'start', '-a', 'com.android.setupwizard.FOUR_CORNER_EXIT']
      )
    except adb.AdbError as e:
      if self._ignore_oobe_error(e):
        # The four corner exit action will not run if the device is already
        # logged in or if the device is not rooted.
        self.controller.log.debug('Ignoring failure to skip OOBE/Setup Wizard.')
        self.controller.log.debug(e)
      else:
        raise e

  def _ignore_oobe_error(self, e: adb.AdbError) -> bool:
    """Checks if the OOBE error is ignorable."""
    return any(
        error_to_ignore in str(e.stderr)
        for error_to_ignore in self._IGNORABLE_OOBE_ERRORS
    )

  def login(self) -> None:
    """Switches to the logged in user."""
    self._switch_user(LOGGED_IN_USER_ID)

  def logout(self) -> None:
    """Switches to the login screen user."""
    self._switch_user(LOGIN_SCREEN_USER_ID)

  def _switch_user(self, user_id: int) -> None:
    """Switches the user on the device."""
    if user_id == self.controller.adb.current_user_id:
      logging.debug('Device is already logged in as user %s.', user_id)
      return
    self.controller.adb.shell(['am', 'switch-user', '-w', str(user_id)])
    if user_id == LOGGED_IN_USER_ID:
      # wait for the launcher to be active before proceeding
      retry.retry(
          lambda: self._ui_active_package_is(self._LAUNCHER_PACKAGE_NAME),
          policy=DETECT_LAUNCHER_AS_ACTIVE_PACKAGE_RETRY_POLICY,
          exceptions=(UnexpectedActivePackageError,),
      )
    # ensure that the user switch was successful
    if user_id != self.controller.adb.current_user_id:
      raise UserSessionError(
          f'Failed to switch user to {user_id}, current user is'
          f' {self.controller.adb.current_user_id}.'
      )

  def _ui_active_package_is(self, expected_package: str) -> None:
    """Checks if the active package is the expected package."""
    try:
      if not self.controller.ui(pkg=expected_package):
        raise UnexpectedActivePackageError(
            expected_package, self.controller.ui.package_name
        )
    except Exception as e:  # pylint: disable=broad-except
      raise UserSessionError(
          f'Failed to check if package {expected_package} is active.'
      ) from e
