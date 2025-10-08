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

"""Additional functionality for Android device used in typec tests."""

import logging
import threading

from lib.utils import retry
from mobly.controllers import android_device
from mobly.controllers.android_device_lib import adb


class TypecAndroidDeviceError(Exception):
  """Error when performing an action on a typec android device."""


class TypecAndroidDevice:
  """Wrapper for Android device for typec tests."""

  BOOT_COMPLETION_TIMEOUT_SECONDS = 3 * 60
  OFFLINE_TIMEOUT_SECONDS = 5

  DEFAULT_RETRY_INTERVAL_SECONDS = 2
  DEFAULT_MAX_RETRIES_OFFLINE = 10
  # add 10 seconds to the total sleep time to account for the time it takes
  # for the device to go to sleep and some overhead
  MIN_SLEEP_TIMER_SECONDS = (
      DEFAULT_RETRY_INTERVAL_SECONDS * DEFAULT_MAX_RETRIES_OFFLINE + 10
  )

  def __init__(self, an_dev: android_device.AndroidDevice):
    self.controller = an_dev

  def _adb_shell_as_user(self, user_id: int | str, cmd: list[str]) -> bytes:
    """Runs adb as the specified user."""
    return self.controller.adb.shell(
        ['su', f'{user_id}'] + cmd,
    )

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

  def reboot(self):
    self.controller.reboot()

  def suspend_with_wakeup_timer(self, wakeup_timeout_seconds: int):
    """Suspends the device with a wakeup timer. This is a blocking call.

    Args:
      wakeup_timeout_seconds: The wakeup timeout in seconds. Must be greater
        than the minimum sleep timer of MIN_SLEEP_TIMER_SECONDS.
    """
    wakeup_timer = self.begin_suspend_with_wakeup_timer(wakeup_timeout_seconds)
    wakeup_timer.join()
    self.end_suspend()

  def begin_suspend_with_wakeup_timer(
      self, wakeup_timeout_seconds: int
  ) -> threading.Timer:
    """Begins suspending the device with a wakeup timer. Non-blocking.

    This function initiates the suspend process and returns immediately
    after the device is offline. The caller is responsible for waiting for
    the device to resume and calling end_suspend after wakeup.

    Args:
      wakeup_timeout_seconds: The wakeup timeout in seconds. Must be greater
        than the minimum sleep timer of MIN_SLEEP_TIMER_SECONDS.

    Returns:
        A threading.Timer object that will fire when the wakeup timeout expires.
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
    return wakeup_timer

  def end_suspend(self):
    """Waits for the device to complete boot and restarts services."""
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
      raise TypecAndroidDeviceError('DUT failed to suspend.')

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
      raise TypecAndroidDeviceError(
          'Unexpected error while checking if device is offline.'
      ) from e
    return True

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
        policy=retry.RetryPolicy(max_tries=max_retries, delay_seconds=interval),
    )

  @property
  def adb(self) -> adb.AdbProxy:
    return self.controller.adb
