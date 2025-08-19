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
import threading
import time

from lib.pasit.android import snippet_tools
from lib.pasit.android import user_session_tools
from lib.pasit.base import base_pasit_device
from lib.utils import retry
from lib.utils import servo_client
from mobly.controllers import android_device
from mobly.controllers.android_device_lib import adb


class AndroidDeviceError(Exception):
  """Error when trying performing an action on an Android device."""


class AndroidPasitDevice(base_pasit_device.BasePasitDevice):
  """AndroidPasitDevice handles the setup of an Android device for PASIT testing."""

  BOOT_COMPLETION_TIMEOUT_SECONDS = 3 * 60
  OFFLINE_TIMEOUT_SECONDS = 5

  DEFAULT_RETRY_INTERVAL_SECONDS = 2
  DEFAULT_MAX_RETRIES_OFFLINE = 10
  # add 10 seconds to the total sleep time to account for the time it takes
  # for the device to go to sleep and some overhead
  MIN_SLEEP_TIMER_SECONDS = (
      DEFAULT_RETRY_INTERVAL_SECONDS * DEFAULT_MAX_RETRIES_OFFLINE + 10
  )

  SCREENSHOTS_PATH = '/data/media/10/Pictures/Screenshots/'
  TMP_DIR = '/data/local/tmp/'

  def __init__(
      self,
      controller: android_device.AndroidDevice,
      servo: servo_client.ServoBase,
  ):
    super().__init__(controller, servo)
    self.snippets = snippet_tools.SnippetTools(self.controller)
    self.user_session = user_session_tools.UserSessionTools(self.controller)

    # must bypass setup wizard before switch to login screen user
    self.controller.root_adb()
    self.user_session.skip_oobe()
    # for consistency across all runs
    # and to make sure that mbs is installed under the login screen user
    self.user_session.switch_to_login_screen_user()
    self._test_settings()
    # uninstall apks to avoid INSTALL_FAILED_UPDATE_INCOMPATIBLE errors
    self.snippets.uninstall_all()
    self.snippets.install_and_load_mbs(user_session_tools.LOGIN_SCREEN_USER_ID)
    self.snippets.register_uiautomator()
    self._bypass_login_screen()

  def cleanup(self):
    self._stop_services()
    # clean up after testing to avoid INSTALL_FAILED_UPDATE_INCOMPATIBLE errors
    self.snippets.uninstall_all()

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
    self.user_session.switch_to_logged_in_user()

  def power_on(self):
    self._request_power_on()
    # TODO: b/414995167 - better way to reduce falkiness
    time.sleep(2)
    self.controller.wait_for_boot_completion(
        timeout=self.BOOT_COMPLETION_TIMEOUT_SECONDS
    )
    # for consistency across all runs, switch to the login screen user first
    # and to make sure that mbs is installed under the login screen user
    self.user_session.switch_to_login_screen_user()
    # need to re-install mbs after power cycle because the stop() for the mbs
    # service uninstalls the mbs apk.
    self.snippets.install_mbs(user_session_tools.LOGIN_SCREEN_USER_ID)
    self.controller.root_adb()
    self._start_services()
    self._bypass_login_screen()
    # if device was previously suspended ensure that the wakelocks are restored
    self._set_wakup_timeout(0)

  def wakeup(self):
    self._request_power_on()
    # TODO: b/414995167 - better way to reduce falkiness
    time.sleep(2)
    self.controller.wait_for_boot_completion(
        timeout=self.BOOT_COMPLETION_TIMEOUT_SECONDS
    )
    self._start_services()
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
    self._start_services()

  def suspend(self):
    self._stop_services()
    self._suspend()

  def _start_services(self):
    logging.debug('Current user: %s', self.controller.adb.current_user_id)
    logging.debug('Starting services...')
    self.controller.services.start_all()

  def _stop_services(self):
    logging.debug('Stopping services...')
    self.controller.services.stop_all()

  def _suspend(self):
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

  def capture_screenshots(self, output_path: str, file_name_prefix: str):
    self.controller.take_screenshot(
        output_path, file_name_prefix, all_displays=True
    )

  def get_screenshots_path(self) -> str:
    return self.SCREENSHOTS_PATH

  def get_temp_dir(self) -> str:
    return self.TMP_DIR

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
