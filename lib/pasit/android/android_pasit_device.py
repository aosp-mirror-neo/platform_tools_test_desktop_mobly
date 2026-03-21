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
import functools
import logging
import threading
import time

from lib.pasit.android import android_ui_tools
from lib.pasit.android import android_user_tools
from lib.pasit.android import dumpsys_battery_parser
from lib.pasit.android import input_recorder
from lib.pasit.android import process_monitor_group
from lib.pasit.android import screen_recorder
from lib.pasit.android import snippet_tools
from lib.pasit.android import ui_watcher
from lib.pasit.base import base_pasit_device
from lib.pasit.base import base_ui_tools
from lib.pasit.base import base_user_tools
from lib.utils import retry
from lib.utils import servo_client
from mobly.controllers import android_device
from mobly.controllers.android_device_lib import adb


PasitDeviceError = base_pasit_device.PasitDeviceError


class AndroidPasitDevice(base_pasit_device.BasePasitDevice):
  """AndroidPasitDevice handles the setup of an Android device for PASIT testing."""

  _BOOT_COMPLETION_TIMEOUT_SECONDS = 3 * 60
  _IS_DEVICE_ONLINE_TIMEOUT_SECONDS = 20

  _DEFAULT_RETRY_INTERVAL_SECONDS = 2
  _DEFAULT_MAX_RETRIES_OFFLINE = 20
  # add 10 seconds to the total sleep time to account for the time it takes
  # for the device to go to sleep and some overhead
  MIN_WAKEUP_TIMEOUT_SECONDS = (
      _DEFAULT_RETRY_INTERVAL_SECONDS * _DEFAULT_MAX_RETRIES_OFFLINE + 10
  )

  SCREENSHOTS_PATH = '/data/media/10/Pictures/Screenshots/'
  TMP_DIR = '/data/local/tmp/'

  _PROCESS_NOT_RESPONDING_PARAMS = ui_watcher.UIWatcherParams(
      text_to_match="Process system isn't responding",
      text_to_click='Close app',
  )

  _ANDROID_SETUP_KEEPS_STOPPING_PARAMS = ui_watcher.UIWatcherParams(
      text_to_match='Android Setup keeps stopping',
      text_to_click='Close app',
  )

  def __init__(
      self,
      controller: android_device.AndroidDevice,
      servo: servo_client.ServoBase,
  ):
    super().__init__(controller, servo)
    self._override_boot_completion_timeout()
    self._wait_for_boot_completion()

    # Override the screenshot timeout from Mobly default values to prevent
    # screenshot failures due to timeout, when screen recording is enabled.
    android_device.TAKE_SCREENSHOT_TIMEOUT_SECOND = 20

    self._snippets = snippet_tools.SnippetTools(self.controller)
    self._ui_watcher = ui_watcher.UIWatcher(self.controller)
    self._user_tools = android_user_tools.AndroidUserTools(self.controller)
    self._ui_tools = android_ui_tools.AndroidUITools(self.controller)
    self._process_monitor_group = process_monitor_group.ProcessMonitorGroup(
        self.controller
    )
    # must bypass setup wizard before switch to login screen user
    self.controller.root_adb()
    self._test_settings()
    self._user_tools.skip_oobe()
    # for consistency across all runs
    # and to make sure that mbs is installed under the login screen user
    self._user_tools.logout()
    # uninstall apks to avoid INSTALL_FAILED_UPDATE_INCOMPATIBLE errors
    self._snippets.uninstall_all()
    self._snippets.install_and_load_mbs(android_user_tools.LOGIN_SCREEN_USER_ID)
    self._snippets.register_uiautomator()
    self._ui_watcher.add(self._PROCESS_NOT_RESPONDING_PARAMS)
    self._ui_watcher.add(self._ANDROID_SETUP_KEEPS_STOPPING_PARAMS)
    self._user_tools.login()
    self._boot_id = None
    self._update_boot_id()

  def _override_boot_completion_timeout(self):
    """Overrides the boot completion timeout to reduce test time.

    Override the boot completion timeout to reduce test time when DUT has
    boot issues. The default from Mobly of 15 minutes is too long for this use
    case.
    """
    # overriding this value only affects function calls that use the default
    # value, which is why we patch wait_for_boot_completion below as well.
    android_device.DEFAULT_TIMEOUT_BOOT_COMPLETION_SECOND = (
        self._BOOT_COMPLETION_TIMEOUT_SECONDS
    )
    # MonkeyPatch AndroidDevice.wait_for_boot_completion to override the
    # timeout in calls to it that use the default value.
    original_wait_for_boot_completion = self.controller.wait_for_boot_completion

    @functools.wraps(original_wait_for_boot_completion)
    def _patched_wait_for_boot_completion(*args, **kwargs):
      kwargs.setdefault('timeout', self._BOOT_COMPLETION_TIMEOUT_SECONDS)
      return original_wait_for_boot_completion(*args, **kwargs)

    self.controller.wait_for_boot_completion = _patched_wait_for_boot_completion

  def cleanup(self):
    self._ui_watcher.remove_all()
    self._stop_services()
    # clean up after testing to avoid INSTALL_FAILED_UPDATE_INCOMPATIBLE errors
    self._snippets.uninstall_all()

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
    # ensure that boot ID is cleared before reboot to avoid false positives
    # if the device fails to boot completely after a reboot.
    self._boot_id = None
    self._process_monitor_group.pause_all()
    self.controller.reboot()
    self._process_monitor_group.resume_all()
    self._update_boot_id()
    self._user_tools.login()

  def cold_reset(self):
    self._boot_id = None
    self._process_monitor_group.pause_all()
    try:
      self._stop_services()
    except Exception as e:  # pylint: disable=broad-except
      logging.warning('Failed to stop services during cold reset: %s', e)
    self._servo.cold_reset()
    self.wait_for_device_online()
    self._power_on_routine()

  def power_on(self, login: bool = True):
    self.request_power_on()
    # TODO: b/414995167 - better way to reduce falkiness
    time.sleep(2)
    self._power_on_routine(login)
    # if device was previously suspended ensure that the wakelocks are restored
    self._set_wakup_timeout(0)

  def _power_on_routine(self, login: bool = True):
    self._wait_for_boot_completion()
    self._process_monitor_group.resume_all()
    self._update_boot_id()
    self.controller.root_adb()
    # for consistency across all runs, switch to the login screen user first
    # and to make sure that mbs is installed under the login screen user
    # TODO: b/nobug - check if logout is still needed here
    if login:
      self._user_tools.logout()
    self._start_services()
    if login:
      self._user_tools.login()

  def power_off(self):
    self._process_monitor_group.pause_all()
    self._stop_services()
    self.request_power_off()
    logging.debug('Waiting for device to power off...')
    self.wait_for_device_offline()
    self._boot_id = None

  def suspend(self):
    self._process_monitor_group.pause_all()
    self._stop_services()
    self._suspend()

  def _wakeup_attempt(self):
    # This is just one way we could acomplish the retries to deal with ADB
    # flakes after wakeup.  Retrying the wait_for_boot_completion is not
    # strictly necessary, but retrying it will not cause any harm or take a long
    # time either.
    self._wait_for_boot_completion()
    # ensure that the device is online with 3 consecutive attempts to reduce
    # flakiness, where the DUT goes offline shortly after wakeup.
    for _ in range(3):
      online = self.is_device_online()
      time.sleep(2)
      if not online:
        logging.warning('Device is not online after boot completion.')
        raise PasitDeviceError('Device is not online after wakeup.')

  def wakeup(self, wakeup_routine_only: bool = False):
    if not wakeup_routine_only:
      self.request_power_on()
      retry.retry(
          self._wakeup_attempt,
          policy=retry.RetryPolicy(max_tries=3, delay_seconds=2),
          exceptions=(PasitDeviceError,),
      )
    if self.unexpected_reboots():
      raise PasitDeviceError('Device rebooted between suspend and wakeup.')
    self._process_monitor_group.resume_all()
    self._start_services()
    # if device was previously suspended ensure that the wakelocks are restored
    self._set_wakup_timeout(0)

  def suspend_with_wakeup_timer(self, wakeup_timeout_seconds: int):
    """Suspends the device with a wakeup timer.

    Args:
      wakeup_timeout_seconds: The wakeup timeout in seconds. Must be greater
        than the minimum timeout of MIN_WAKEUP_TIMEOUT_SECONDS.
    """
    if wakeup_timeout_seconds < self.MIN_WAKEUP_TIMEOUT_SECONDS:
      raise ValueError(
          f'Wakeup timeout {wakeup_timeout_seconds} is less than the minimum'
          f' sleep timer {self.MIN_WAKEUP_TIMEOUT_SECONDS}.'
      )
    self._process_monitor_group.pause_all()
    self._stop_services()
    self._set_wakup_timeout(wakeup_timeout_seconds)
    wakeup_timer = threading.Timer(wakeup_timeout_seconds, lambda: None)
    wakeup_timer.start()
    self._suspend()

    wakeup_timer.join()
    self._wait_for_boot_completion()
    self._process_monitor_group.resume_all()
    self._start_services()

  def is_device_online(self) -> bool:
    try:
      self.controller.adb.shell(
          ['echo', 'hello'],
          timeout=self._IS_DEVICE_ONLINE_TIMEOUT_SECONDS,
      )
    except adb.AdbTimeoutError:
      logging.debug('Device is not adb detectable, device is offline.')
      return False
    except adb.AdbError as e:
      if (
          'closed' in str(e.stderr)
          or 'device offline' in str(e.stderr)
          or 'not found' in str(e.stderr)
      ):
        logging.debug('Device detected as offline.')
        return False
      if e.ret_code == 255:
        # Handle return code 255 to avoid flakes.
        logging.debug('Device is not adb detectable, device is offline.')
        return False
      raise PasitDeviceError(
          'Unexpected error while checking if device is offline.'
      ) from e
    return True

  def capture_screenshots(self, output_path: str, file_name_prefix: str):
    try:
      self.controller.take_screenshot(
          output_path, file_name_prefix, all_displays=True
      )
    except adb.AdbError as e:
      logging.error('Failed to capture screenshot: %s', e)

  def get_screenshots_path(self) -> str:
    return self.SCREENSHOTS_PATH

  def get_temp_dir(self) -> str:
    return self.TMP_DIR

  def is_powered(self) -> bool:
    return dumpsys_battery_parser.DumpsysBatteryParser(
        self.controller
    ).is_powered()

  def _get_boot_id(self) -> str:
    return (
        self.shell(['cat', '/proc/sys/kernel/random/boot_id'])
        .decode('utf-8')
        .strip()
    )

  def _update_boot_id(self) -> None:
    self._boot_id = self._get_boot_id()

  def unexpected_reboots(self) -> bool:
    current_boot_id = self._get_boot_id()
    if self._boot_id and self._boot_id != current_boot_id:
      logging.error(
          'Device rebooted unexpectedly (boot_id changed from %s to %s)',
          self._boot_id,
          current_boot_id,
      )
      return True
    return False

  def recover_unexpected_reboot(self):
    if not self.unexpected_reboots():
      return
    try:
      # pause before stop seems to work through the unexpected reboot, while
      # _stop_services() alone does not.
      self.controller.services.pause_all()
      self._stop_services()
      self._snippets.reinstall_uiautomator()
      self._power_on_routine()
    except Exception as e:  # pylint: disable=broad-except
      raise PasitDeviceError('Failed to recover from unexpected reboot.') from e
    # check uiautomator after recovery to ensure that mobly services/snippets
    # are running properly, better to raise an error before the next test
    # starts rather than have the next test fail.
    try:
      retry.retry(
          lambda: self.controller.ui.package_name,
          policy=retry.RetryPolicy(max_tries=3, delay_seconds=1),
          exceptions=(Exception,),
      )
    except Exception as e:  # pylint: disable=broad-except
      raise PasitDeviceError(
          'Failed to recover from unexpected reboot, uiautomator is not'
          ' available.'
      ) from e

  def start_screen_recording(self):
    self._process_monitor_group.start(screen_recorder.ScreenRecorder)

  def stop_screen_recording(self, output_path: str):
    self._process_monitor_group.stop(
        screen_recorder.ScreenRecorder, output_path
    )

  def start_input_recording(self):
    self._process_monitor_group.start(input_recorder.InputRecorder)

  def stop_input_recording(self, output_path: str):
    self._process_monitor_group.stop(input_recorder.InputRecorder, output_path)

  @property
  def user_tools(self) -> base_user_tools.BaseUserTools:
    return self._user_tools

  @property
  def ui_tools(self) -> base_ui_tools.BaseUITools:
    return self._ui_tools

  def _wait_for_boot_completion(self):
    try:
      self.controller.wait_for_boot_completion(
          timeout=self._BOOT_COMPLETION_TIMEOUT_SECONDS
      )
    except android_device.DeviceError as e:
      if self.is_device_online():
        raise PasitDeviceError(
            'Device is online but did not boot completely within'
            f' {self._BOOT_COMPLETION_TIMEOUT_SECONDS} seconds.'
        ) from e
      raise PasitDeviceError(
          'Device not online after timeout'
          f' {self._BOOT_COMPLETION_TIMEOUT_SECONDS} seconds.'
      ) from e

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
    self.wait_for_device_offline()

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
        # Fail safe way to disable setup wizard, this will ensure that if setup
        # wizard crashes it will not try to start up again after reboot.
        ('user_setup_complete', '1'),
        ('device_provisioned', '1'),
    ]
    for setting, value in settings:
      self.controller.adb.shell(['settings', 'put', 'global', setting, value])

    # show seconds on the time for better debugability
    self.controller.adb.shell(
        ['settings', 'put', 'secure', 'clock_seconds', '1']
    )

  def _adb_shell_as_user(self, user_id: int | str, cmd: list[str]) -> bytes:
    """Runs adb as the specified user."""
    return self.controller.adb.shell(
        ['su', f'{user_id}'] + cmd,
    )
