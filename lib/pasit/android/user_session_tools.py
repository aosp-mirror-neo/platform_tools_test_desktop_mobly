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

"""UserSessionTools provides tools for managing user sessions on an Android device."""

import logging

from mobly.controllers import android_device
from mobly.controllers.android_device_lib import adb

LOGGED_IN_USER_ID = 10
LOGIN_SCREEN_USER_ID = 0


class UserSessionError(Exception):
  """Raised when there is an error managing user sessions on an Android device."""


class UserSessionTools:
  """UserSessionTools provides tools for managing user sessions on an Android device."""

  _FOUR_CORNER_EXIT_ACTION_ERROR = (
      'Activity not started, unable to resolve Intent'
  )

  def __init__(
      self,
      controller: android_device.AndroidDevice,
  ):
    self.controller = controller

  def skip_oobe(self):
    """Skips the OOBE flow."""
    # Skip OOBE/Setup Wizard - go/skip-oobe
    try:
      self.controller.adb.shell(
          ['am', 'start', '-a', 'com.android.setupwizard.FOUR_CORNER_EXIT']
      )
    except adb.AdbError as e:
      if self._FOUR_CORNER_EXIT_ACTION_ERROR in str(e.stderr):
        # The four corner exit action will not run if the device is already
        # logged in or if the device is not rooted.
        self.controller.log.debug('Ignoring failure to skip OOBE/Setup Wizard.')
        self.controller.log.debug(e)
      else:
        raise e

  def switch_user(self, user_id: int):
    """Switches the user on the device.

    Args:
      user_id: The user ID to switch to.

    Raises:
      UserSessionError: If the user switch fails.
    """
    if user_id == self.controller.adb.current_user_id:
      logging.debug('Device is already logged in as user %s.', user_id)
      return
    self.controller.adb.shell(['am', 'switch-user', '-w', str(user_id)])
    # ensure that the user switch was successful
    if user_id != self.controller.adb.current_user_id:
      raise UserSessionError(
          f'Failed to switch user to {user_id}, current user is'
          f' {self.controller.adb.current_user_id}.'
      )
