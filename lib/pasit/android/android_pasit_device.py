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

"""AndroidPasitDevice handles the setup of an Android device for PASIT testing."""

from collections.abc import Iterable
import logging
import os
import sys
import threading
import time

from lib.pasit.base import base_pasit_device
from lib.utils import retry
from mobly.controllers import android_device
from mobly.controllers.android_device_lib import adb
from mobly.controllers.android_device_lib import apk_utils
from mobly.controllers.android_device_lib import snippet_client_v2
from snippet_uiautomator import uiautomator


class AndroidDeviceError(Exception):
  """Error when trying performing an action on an Android device."""


class UnexpectedActivePackageError(Exception):
  """Error when the active package is not the expected package."""

  def __init__(self, expected_package: str, actual_package: str):
    super().__init__(
        f'Expected package {expected_package} to be active, but'
        f' {actual_package} is active.'
    )
    self.expected_package = expected_package
    self.actual_package = actual_package


class AndroidPasitDevice(base_pasit_device.BasePasitDevice):
  """AndroidPasitDevice handles the setup of an Android device for PASIT testing."""

  FOUR_CORNER_EXIT_ACTION_ERROR = (
      'Activity not started, unable to resolve Intent'
  )
  LOGGED_IN_USER_ID = 10
  LOGIN_SCREEN_USER_ID = 0
  BOOT_COMPLETION_TIMEOUT_SECONDS = 3 * 60
  OFFLINE_TIMEOUT_SECONDS = 5

  LOGIN_SCREEN_PACKAGE_NAME = 'com.google.android.desktop.identity.login'
  LAUNCHER_PACKAGE_NAME = 'com.google.android.apps.nexuslauncher'
  DEFAULT_RETRY_INTERVAL_SECONDS = 2
  DEFAULT_MAX_RETRIES_OFFLINE = 10
  # add 10 seconds to the total sleep time to account for the time it takes
  # for the device to go to sleep and some overhead
  MIN_SLEEP_TIMER_SECONDS = (
      DEFAULT_RETRY_INTERVAL_SECONDS * DEFAULT_MAX_RETRIES_OFFLINE + 10
  )

  # snippet apk is in same directory as this mobly executable
  SNIPPET_APK_PATH = os.path.join(
      os.path.dirname(os.path.abspath(sys.argv[0])),
      'mobly-bundled-snippets.apk',
  )
  UIAUTOMATOR_APK_PATH = os.path.join(
      os.path.dirname(os.path.abspath(sys.argv[0])),
      'snippet-uiautomator.apk',
  )

  def __init__(self, controller: android_device.AndroidDevice, servo_uri: str):
    super().__init__(controller, servo_uri)
    self._test_settings()
    # uninstall apks to avoid INSTALL_FAILED_UPDATE_INCOMPATIBLE errors
    self.uninstall_apks()
    self._install_mbs()
    self._load_mbs()
    self._register_uiautomator()
    self.controller.root_adb()
    self._skip_oobe()
    self._bypass_login_screen()

  def __del__(self):
    # clean up after testing to avoid INSTALL_FAILED_UPDATE_INCOMPATIBLE errors
    self.uninstall_apks()

  def uninstall_apks(self):
    apk_utils.uninstall(self.controller, android_device.MBS_PACKAGE)
    apk_utils.uninstall(self.controller, uiautomator.UIAUTOMATOR_PACKAGE_NAME)

  def _test_settings(self):
    # settings are same settings set by tradefed for GoogleDeviceSetup
    settings = [
        (
            'verifier_verify_adb_installs',
            '0',
        ),  # disable app verification
        ('verifier_engprod', '1'),  # disable play protect prompts
        (
            'google_play_store_system_component_update',
            '0',
        ),  # disable automatic installation of system component updates
        ('google_play_store_system_component_update_last_user_id', '-1'),
        ('google_ota_automatic_download', '0'),
        ('hide_error_dialogs', '1'),
    ]
    for setting, value in settings:
      self.controller.adb.shell(['settings', 'put', 'global', setting, value])

  def shell(self, params: Iterable[str]) -> bytes:
    try:
      return self.controller.adb.shell(params)
    except adb.AdbError as e:
      raise base_pasit_device.ShellError(
          command=e.cmd,
          stdout=e.stdout,
          stderr=e.stderr,
          return_code=e.ret_code,
          device_uri=self.controller.serial,
      ) from e

  def reboot(self):
    self.controller.reboot()
    self._bypass_login_screen()

  def _bypass_login_screen(self):
    self._switch_user(self.LOGGED_IN_USER_ID)

  def power_on(self):
    self._request_power_on()
    # TODO: b/414995167 - better way to reduce falkiness
    time.sleep(2)
    self.controller.wait_for_boot_completion(
        timeout=self.BOOT_COMPLETION_TIMEOUT_SECONDS
    )
    # need to re-install mbs after power cycle because the stop() for the mbs
    # service uninstalls the mbs apk.
    self._install_mbs()
    self.controller.root_adb()
    logging.debug('Starting services...')
    self.controller.services.start_all()
    self._bypass_login_screen()
    # if device was previously suspended ensure that the wakelocks are restored
    self._set_wakup_timeout(0)

  def power_off(self):
    self._stop_services()
    self._request_power_off()
    logging.debug('Waiting for device to power off...')
    if not self._wait_for_device_offline():
      raise AndroidDeviceError('DUT failed to power off.')

  def _set_wakup_timeout(self, wakeup_timeout_seconds: int):
    self._adb_shell_as_user(
        # this command must be run as non-root user or it will fail so run
        # as user "shell", shell is the default user when running adb commands
        # when not using adb root
        'shell',
        [
            'cmd',
            'power',
            'wakeup',
            str(wakeup_timeout_seconds * 1000),  # wakeup expects milliseconds
            '--restore-wakelocks',
        ],
    )

  def suspend_with_wakeup_timer(self, wakeup_timeout_seconds: int):
    """Suspends the device with a wakeup timer.

    Args:
      wakeup_timeout_seconds: The wakeup timeout in seconds. Must be greater
        than the minimum sleep timer of MIN_SLEEP_TIMER_SECONDS.
    """
    if wakeup_timeout_seconds < self.MIN_SLEEP_TIMER_SECONDS:
      raise ValueError(
          f'Wakeup timeout {wakeup_timeout_seconds} is less than the minimum'
          f' sleep timer {self.MIN_SLEEP_TIMER_SECONDS}.'
      )
    self._stop_services()
    self._set_wakup_timeout(wakeup_timeout_seconds)
    wakeup_timer = threading.Timer(wakeup_timeout_seconds, lambda: None)
    wakeup_timer.start()
    self._suspend()

    wakeup_timer.join()
    self.controller.wait_for_boot_completion(
        timeout=self.BOOT_COMPLETION_TIMEOUT_SECONDS
    )
    logging.debug('Starting services...')
    self.controller.services.start_all()

  def suspend(self):
    self._stop_services()
    self._suspend()

  def _stop_services(self):
    logging.debug('Stopping services...')
    self.controller.services.stop_all()

  def _suspend(self):
    # temporary test if the kernel wake lock is held
    logging.debug(
        'Held kernel wake lock: %s',
        self.controller.adb.shell(['cat', '/sys/power/wake_lock']),
    )
    self.controller.adb.shell(['cmd', 'power', 'sleep', '--disable-wakelocks'])
    logging.debug('Waiting for device to suspend...')
    if not self._wait_for_device_offline():
      raise AndroidDeviceError('DUT failed to suspend.')

  def is_device_online(self, timeout: int) -> bool:
    try:
      self.controller.adb.shell(['echo', 'hello'], timeout=timeout)
    except adb.AdbTimeoutError:
      logging.debug('Device is not adb detectable, device is offline.')
      return False
    except adb.AdbError as e:
      if 'closed' in str(e.stderr) or 'device offline' in str(e.stderr):
        logging.debug('Device detected as offline.')
        return False
      raise AndroidDeviceError(
          'Unexpected error while checking if device is offline.'
      ) from e
    return True

  def get_screenshots(self, output_path: str, file_name_prefix: str):
    self.controller.take_screenshot(
        output_path, file_name_prefix, all_displays=True
    )

  def _install_mbs(self):
    """Installs Mobly Bundled Snippets."""
    apk_utils.install(
        self.controller,
        self.SNIPPET_APK_PATH,
        user_id=self.LOGIN_SCREEN_USER_ID,
    )

  def _register_uiautomator(self):
    """Installs UI Automator."""
    snippet = uiautomator.Snippet()
    snippet.file_path = str(self.UIAUTOMATOR_APK_PATH)
    self.controller.services.register(
        uiautomator.ANDROID_SERVICE_NAME,
        uiautomator.UiAutomatorService,
        configs=uiautomator.UiAutomatorConfigs(snippet=snippet),
    )

  def _load_mbs(self):
    self.controller.load_snippet(
        'mbs',
        android_device.MBS_PACKAGE,
        config=snippet_client_v2.Config(user_id=self.LOGIN_SCREEN_USER_ID),
    )

  def _skip_oobe(self):
    """Skips the OOBE flow."""
    # Skip OOBE/Setup Wizard - go/skip-oobe
    try:
      self.controller.adb.shell(
          ['am', 'start', '-a', 'com.android.setupwizard.FOUR_CORNER_EXIT']
      )
    except adb.AdbError as e:
      if self.FOUR_CORNER_EXIT_ACTION_ERROR in str(e.stderr):
        # The four corner exit action will not run if the device is already
        # logged in or if the device is not rooted.
        self.controller.log.debug('Ignoring failure to skip OOBE/Setup Wizard.')
        self.controller.log.debug(e)
      else:
        raise e

  def _switch_user(self, user_id: int):
    """Switches the user on the device."""
    if user_id == self.controller.adb.current_user_id:
      logging.debug('Device is already logged in as user %s.', user_id)
      return
    if user_id == self.LOGGED_IN_USER_ID:
      # if switching to the logged in user ensure that login screen is shown
      # before attempting to switch users
      retry.retry(
          lambda: self._ui_active_package_is(self.LOGIN_SCREEN_PACKAGE_NAME),
          max_tries=10,
          exceptions=(UnexpectedActivePackageError,),
      )
    self.controller.adb.shell(['am', 'switch-user', str(user_id)])
    # wait for the launcher to be active before proceeding
    retry.retry(
        lambda: self._ui_active_package_is(self.LAUNCHER_PACKAGE_NAME),
        max_tries=10,
        exceptions=(UnexpectedActivePackageError,),
    )
    # ensure that the user switch was successful
    if user_id != self.controller.adb.current_user_id:
      raise AndroidDeviceError(
          f'Failed to switch user to {user_id}, current user is'
          f' {self.controller.adb.current_user_id}.'
      )

  def _ui_active_package_is(self, expected_package: str):
    """Checks if the active package is the expected package."""
    if not self.controller.ui(pkg=expected_package):
      raise UnexpectedActivePackageError(
          expected_package, self.controller.ui.package_name
      )

  def _wait_for_device_offline(
      self,
      interval: int = DEFAULT_RETRY_INTERVAL_SECONDS,
      max_retries: int = DEFAULT_MAX_RETRIES_OFFLINE,
  ) -> bool:
    """Waits for the device to be offline.

    Args:
      interval: The interval between retries.
      max_retries: The maximum number of retries.

    Returns:
      True if the device is offline, False if the device is online.
    """
    return retry.retry(
        lambda: not self.is_device_online(self.OFFLINE_TIMEOUT_SECONDS),
        until=lambda is_offline: is_offline,
        max_tries=max_retries,
        delay_seconds=interval,
    )

  def _adb_shell_as_user(self, user_id: int | str, cmd: list[str]) -> bytes:
    """Runs adb as the specified user."""
    return self.controller.adb.shell(
        ['su', f'{user_id}'] + cmd,
    )
