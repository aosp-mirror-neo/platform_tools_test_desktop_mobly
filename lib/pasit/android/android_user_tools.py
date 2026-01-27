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

import datetime
import logging

from lib.pasit.base import base_user_tools
from lib.utils import retry
from mobly.controllers import android_device
from mobly.controllers.android_device_lib import adb
from snippet_uiautomator import uiautomator

LOGGED_IN_USER_ID = 10
LOGIN_SCREEN_USER_ID = 0

DETECT_LAUNCHER_PACKAGE_RETRY_POLICY = retry.RetryPolicy(
    max_tries=10, delay_seconds=1
)
DETECT_GUEST_MODE_AS_ACTIVE_USER_RETRY_POLICY = retry.RetryPolicy(
    max_tries=15, delay_seconds=1
)
LOCK_UNLOCK_RETRY_POLICY = retry.RetryPolicy(max_tries=10, delay_seconds=1)


class AndroidUserTools(base_user_tools.BaseUserTools):
  """AndroidUserTools provides tools for managing user sessions on an Android device."""

  _PIN = '1234'
  _IGNORABLE_OOBE_ERRORS = (
      'Activity not started, unable to resolve Intent',
      'Activity not started, not allowed for the given user',
  )
  _LAUNCHER_PACKAGE_NAME = 'com.google.android.apps.nexuslauncher'
  _SYSUI_PACKAGE_NAME = 'com.android.systemui'

  def __init__(self, controller: android_device.AndroidDevice):
    self.controller = controller
    self._clear_lock_pin()

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

  def login(self) -> None:
    """Switches to the logged in user."""
    self._switch_user(LOGGED_IN_USER_ID)
    # we should be logged in and unlocked after login command completes
    self.unlock()

  def logout(self) -> None:
    """Switches to the login screen user."""
    self._switch_user(LOGIN_SCREEN_USER_ID)

  def guest_mode(self) -> None:
    """Enters guest mode."""
    self.logout()
    self.controller.log.info('Entering guest mode')
    # Click the "Use as guest" button on the login screen.
    use_as_guest_button = self.controller.ui(text='Use as guest')
    if not use_as_guest_button.wait.exists(
        timeout=datetime.timedelta(seconds=10)
    ):
      raise base_user_tools.UserToolsError(
          'Failed to find "Use as guest" button on the login screen.'
      )
    use_as_guest_button.click()
    # Wait for the user ID to switch to a guest ID.
    retry.retry(
        self._is_guest_user,
        until=lambda is_guest_user: is_guest_user,
        policy=DETECT_GUEST_MODE_AS_ACTIVE_USER_RETRY_POLICY,
    )
    # Wait for the launcher to be active to indicate that guest mode has been
    # entered.
    self._verify_launcher_exists()
    if self.session_status() != base_user_tools.SessionStatus.GUEST:
      raise base_user_tools.UserToolsError(
          'Failed to enter guest mode, current status is'
          f' {self.session_status()} and current user is'
          f' {self.controller.adb.current_user_id}.'
      )
    logging.info(
        'Guest mode entered, running as Guest user %s.',
        self.controller.adb.current_user_id,
    )

  def lock(self) -> None:
    if self.session_status() != base_user_tools.SessionStatus.LOGGED_IN:
      raise base_user_tools.UserToolsError(
          'Cannot lock device when it is not logged in, current status is'
          f' {self.session_status()}.'
      )
    if not self._has_pin_set():
      # a lock pin is required to lock the device
      self._set_lock_pin()
    self.controller.log.info('Locking device')
    self.controller.ui.press(uiautomator.KeyEvent.KEYCODE_POWER)
    status = retry.retry(
        self.session_status,
        until=lambda status: status == base_user_tools.SessionStatus.LOCKED,
        policy=LOCK_UNLOCK_RETRY_POLICY,
    )
    if status != base_user_tools.SessionStatus.LOCKED:
      raise base_user_tools.UserToolsError(
          f'Failed to lock device, current status is {status}.'
      )

  def unlock(self) -> None:
    if self.session_status() != base_user_tools.SessionStatus.LOCKED:
      return
    self.controller.log.info('Unlocking device')
    self.controller.adb.shell(['input', 'text', self._PIN])
    self.controller.ui.press(uiautomator.KeyEvent.KEYCODE_ENTER)
    # ensure that the lock pin is cleared after unlocking so subsequent tests
    # don't get locked out
    self._clear_lock_pin()
    status = retry.retry(
        self.session_status,
        until=lambda status: status == base_user_tools.SessionStatus.LOGGED_IN,
        policy=LOCK_UNLOCK_RETRY_POLICY,
    )
    if status != base_user_tools.SessionStatus.LOGGED_IN:
      raise base_user_tools.UserToolsError(
          f'Failed to unlock device, current status is {status}.'
      )

  def session_status(self) -> base_user_tools.SessionStatus:
    if self._is_locked():
      return base_user_tools.SessionStatus.LOCKED
    current_user_id = self.controller.adb.current_user_id
    if current_user_id == LOGGED_IN_USER_ID:
      return base_user_tools.SessionStatus.LOGGED_IN
    if current_user_id == LOGIN_SCREEN_USER_ID:
      return base_user_tools.SessionStatus.LOGGED_OUT
    if self._is_guest_user():
      return base_user_tools.SessionStatus.GUEST
    raise base_user_tools.UserToolsError(
        'Could not determine user session status, current user is'
        f' {current_user_id}.'
    )

  def _is_guest_user(self) -> bool:
    # guest user IDs are dynamically generated so we cannot check for a
    # specific guest user ID. Instead we check that the user ID is greater
    # than the logged in user ID since the dynamic gues user ID is always
    # greater than the logged in user ID.
    return self.controller.adb.current_user_id > LOGGED_IN_USER_ID

  def _ignore_oobe_error(self, e: adb.AdbError) -> bool:
    """Checks if the OOBE error is ignorable."""
    return any(
        error_to_ignore in str(e.stderr)
        for error_to_ignore in self._IGNORABLE_OOBE_ERRORS
    )

  def _switch_user(self, user_id: int) -> None:
    """Switches the user on the device."""
    if user_id != self.controller.adb.current_user_id:
      logging.debug('Switching user to %s.', user_id)
      # Only run the switch-user command if the user is not the current user,
      # but still run the checks to ensure that the user switch was successful
      # even if the switch-user command was not run.
      self.controller.adb.shell(['am', 'switch-user', '-w', str(user_id)])
    if user_id != self.controller.adb.current_user_id:
      raise base_user_tools.UserToolsError(
          f'Failed to switch user to {user_id}, current user is'
          f' {self.controller.adb.current_user_id}.'
      )
    if user_id == LOGGED_IN_USER_ID:
      # this is a fail safe to work around a known issue where sometimes the
      # setup wizard does not get properly skipped due to crashes/ANRs, and
      # as a result the launcher package is not found.
      self.skip_oobe()
      self._verify_launcher_exists()

  def _verify_launcher_exists(self) -> None:
    # wait for the launcher to be active before proceeding
    exists = retry.retry(
        lambda: self._ui_package_exists(self._LAUNCHER_PACKAGE_NAME),
        until=lambda exists: exists,
        policy=DETECT_LAUNCHER_PACKAGE_RETRY_POLICY,
    )
    if not exists:
      self.controller.take_screenshot(
          self.controller.log_path, 'launcher_verify_failure'
      )
      raise base_user_tools.UserToolsError(
          'Failed to find launcher package when logged in'
          f' {self._LAUNCHER_PACKAGE_NAME} is does not exist.'
      )

  def _ui_package_exists(self, package_name: str) -> bool:
    """Checks if a UI element with the given package name exists.

    Args:
      package_name: The package name to check for.

    Returns:
      True if a UI element with the given package name exists, False otherwise.
    """
    package_info = self.controller.ui(pkg=package_name)
    return package_info is not None and package_info.exists

  def _has_pin_set(self) -> bool:
    # use the locksettings command to check if the lock pin is set because the
    # locksettings cli will return 'true' for the get-disabled command if a lock
    # PIN is not set.
    lock_settings_output = self.controller.adb.shell(
        ['locksettings', 'get-disabled']
    )
    return 'true' not in lock_settings_output.decode('utf-8')

  def _is_locked(self) -> bool:
    try:
      # Check to ensure that we are on the lock screen. Since the current user
      # is going to be the logged in user when the device is in the logged in
      # or the locked state, we use the sysui package as a proxy to check if the
      # device is locked.  So if the SYSUI package is not active then the device
      # cannot be in the locked state.
      if not self._ui_package_exists(self._SYSUI_PACKAGE_NAME):
        return False
    except Exception as e:  # pylint: disable=broad-except
      logging.debug(
          'Failed to check if sysui package exists, assuming device is'
          ' not locked: %s.',
          e,
      )
      return False
    return (
        self._has_pin_set()
        and self.controller.adb.current_user_id == LOGGED_IN_USER_ID
    )

  def _set_lock_pin(self) -> None:
    """Sets the lock pin."""
    if self._has_pin_set():
      return
    self.controller.adb.shell(['locksettings', 'set-pin', self._PIN])

  def _clear_lock_pin(self) -> None:
    if not self._has_pin_set():
      return
    try:
      self.controller.adb.shell(['locksettings', 'clear', '--old', self._PIN])
    except adb.AdbError as e:
      raise base_user_tools.UserToolsError(
          'Failed to clear lock pin. DUT cannot be tested in this state,'
          ' please wipe the device or manually clear the lock pin.'
      ) from e
