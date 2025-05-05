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

from mobly.controllers import android_device
from mobly.controllers.android_device_lib import adb
from mobly.controllers.android_device_lib import apk_utils
from mobly.controllers.android_device_lib import snippet_client_v2

from pasit.lib import pasit_utils
from pasit.lib.base import base_pasit_device
import os
import sys


class AndroidDeviceError(Exception):
  """Error when trying performing an action on an Android device."""


class AndroidPasitDevice(base_pasit_device.BasePasitDevice):
  """AndroidPasitDevice handles the setup of an Android device for PASIT testing."""

  FOUR_CORNER_EXIT_ACTION_ERROR = (
      'Activity not started, unable to resolve Intent'
  )
  LOGGED_IN_USER_ID = 10
  LOGIN_SCREEN_USER_ID = 0
  BOOT_COMPLETION_TIMEOUT_SECONDS = 3 * 60
  OFFLINE_TIMEOUT_SECONDS = 5

  # snippet apk is in same directory as this mobly executable
  SNIPPET_APK_PATH = os.path.join(
      os.path.dirname(os.path.abspath(sys.argv[0])),
      'mobly-bundled-snippets.apk',
  )

  def __init__(self, controller: android_device.AndroidDevice, servo_uri: str):
    super().__init__(controller, servo_uri)
    self._test_settings()
    self._install_mbs()
    self._load_mbs()
    self.controller.root_adb()
    self._skip_oobe()
    # Bypass the login screen.
    self._switch_user(self.LOGGED_IN_USER_ID)

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
      self.controller.adb.shell(
          ['settings', 'put', 'global', setting, value]
      )

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

  def power_on(self):
    self._request_power_on()
    self.controller.wait_for_boot_completion(
        timeout=self.BOOT_COMPLETION_TIMEOUT_SECONDS
    )
    # need to re-install mbs after power cycle because the stop() for the mbs
    # service uninstalls the mbs apk.
    self._install_mbs()
    self.controller.root_adb()
    logging.debug('Starting services...')
    self.controller.services.start_all()

  def power_off(self):
    logging.debug('Stopping services...')
    self.controller.services.stop_all()
    self._request_power_off()
    logging.debug('Waiting for device to power off...')
    try:
      self._wait_for_device_offline()
    except AndroidDeviceError as e:
      raise AndroidDeviceError('DUT failed to power off.') from e

  def suspend(self):
    logging.debug('Stopping services...')
    self.controller.services.stop_all()
    self.controller.adb.shell(['input', 'keyevent', 'KEYCODE_SLEEP'])
    logging.debug('Waiting for device to suspend...')
    try:
      self._wait_for_device_offline()
    except AndroidDeviceError as e:
      raise AndroidDeviceError('DUT failed to suspend.') from e

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

  def _install_mbs(self):
    """Installs Mobly Bundled Snippets."""
    apk_utils.uninstall(self.controller, android_device.MBS_PACKAGE)
    apk_utils.install(
        self.controller,
        self.SNIPPET_APK_PATH,
        user_id=self.LOGIN_SCREEN_USER_ID,
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
        self.controller.log.info('Ignoring failure to skip OOBE/Setup Wizard.')
        self.controller.log.info(e)
      else:
        raise e

  def _switch_user(self, user_id: int):
    """Switches the user on the device."""
    self.controller.adb.shell(['am', 'switch-user', str(user_id)])

  def _wait_for_device_offline(
      self, interval: int = 2, max_retries: int = 10
  ) -> None:
    """Waits for the device to be offline."""
    pasit_utils.retry_function(
        self.controller.log,
        self._expect_device_offline,
        max_tries=max_retries,
        delay_seconds=interval,
        exceptions=(AndroidDeviceError,),
    )

  def _expect_device_offline(self) -> None:
    """Checks if the device is offline.

    If the device is offline, it is not adb detectable and an exception is
    raised.

    Returns:
      None if the device is online.

    Raises:
      AndroidDeviceError: If the device is still detectable as online.
    """

    if self.is_device_online(self.OFFLINE_TIMEOUT_SECONDS):
      raise AndroidDeviceError(
          'Device is still adb detectable. Waiting for device offline complete.'
      )
