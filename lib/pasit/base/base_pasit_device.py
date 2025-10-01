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

"""Interface for device operations for PASIT testing."""

import abc
from collections.abc import Iterable
import logging
from typing import Any

from lib.utils import servo_client

DEFAULT_WAIT_FOR_DEVICE_ONLINE_TIMEOUT_SECONDS = 120


class ShellError(Exception):
  """Raised when a shell command fails.

  Attributes:
    command: The command that was executed.
    return_code: The return code of the command.
    stdout: The stdout of the command.
    stderr: The stderr of the command.
    device_uri: The uri of the device.
  """

  def __init__(
      self,
      command: str,
      return_code: int,
      stdout: bytes,
      stderr: bytes,
      device_uri: str,
  ):
    self.command = command
    self.return_code = return_code
    self.stdout = stdout
    self.stderr = stderr
    self.device_uri = device_uri


class ServoNotConfiguredError(Exception):
  """Error when Servo is not configured."""


class DeviceNotOnlineError(Exception):
  """Error when device is not online."""


class BasePasitDevice(metaclass=abc.ABCMeta):
  """Represents a device being tested by PASIT.

  Attributes:
    controller: Mobly controller instance for the tested device.
  """

  def __init__(
      self, controller: Any, servo: servo_client.ServoBase | None = None
  ):
    """Initializes the PasitDevice.

    Args:
      controller: The controller to use for the PASIT device.
      servo: The client to use to interact with the servo.
    """
    self.controller = controller
    self._servo = servo

  @abc.abstractmethod
  def cleanup(self):
    """Cleans up the device after testing."""
    raise NotImplementedError

  @abc.abstractmethod
  def shell(self, params: Iterable[str]) -> bytes:
    """Sends the given parameters to the console.

    Args:
      params: The command to execute, e.g. ['ls', '-la'], as a list of strings,
        each string being a token after splitting the command by spaces.

    Returns:
      The output of the command as bytes.

    Raises:
      ShellError: If the command fails.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def reboot(self):
    """Reboots the device."""
    raise NotImplementedError

  @abc.abstractmethod
  def power_on(self):
    """Powers on the device."""
    raise NotImplementedError

  @abc.abstractmethod
  def power_off(self):
    """Powers off the device."""
    raise NotImplementedError

  @abc.abstractmethod
  def wait_for_device_online(self, timeout: int):
    """Waits for the device to be online with a specific timeout.

    Args:
      timeout: The timeout in seconds to wait for the device to be online.

    Raises:
      DeviceNotOnlineError: If the device is not online after the timeout.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def suspend(self):
    """Suspends the device and waits for it to be offline.

    This will block only until the device is suspended and is not detectable.
    The device will remain suspended until woken through another means and this
    will return after the device is suspended.

    Raises:
      Implementation specific exceptions, if the device fails to suspend.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def wakeup(self):
    """Wakes up the device from suspend and waits for it to be online.

    Will also ensure that the device is logged in after waking up.

    Raises:
      Implementation specific exceptions, if the device fails to wake up.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def suspend_with_wakeup_timer(self, wakeup_timeout_seconds: int):
    """Suspends the device with optional wakup_timeout in seconds.

    This will block for wakeup_timeout_seconds and then block
    until the device has woken up and is reconnected, or the reconnection
    timeout is reached.

    Args:
      wakeup_timeout_seconds: The timeout in seconds to wake up the device in.

    Raises:
      Implementation specific exceptions, if the device fails to suspend or
      fails to reconnect after wakeup_timeout_seconds of suspend.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def is_device_online(self, timeout: int) -> bool:
    """Checks if the device is online."""
    raise NotImplementedError

  def power_on_if_offline(self, timeout: int = 5) -> bool:
    """Performs a cold reset on the device to attempt to reconnect it.

    Args:
      timeout: The timeout in seconds to wait for the device to be online.

    Returns:
      True if device was offline.
    """
    if not self.is_device_online(timeout):
      if self._servo:
        logging.debug('Device is offline, performing cold reset...')
        self._servo.cold_reset()
        try:
          self.wait_for_device_online(
              DEFAULT_WAIT_FOR_DEVICE_ONLINE_TIMEOUT_SECONDS
          )
        except DeviceNotOnlineError:
          logging.error('Device is still offline after cold reset.')
      return True
    return False

  def is_servo_configured(self) -> bool:
    """Returns True if Servo is configured."""
    return self._servo is not None

  @abc.abstractmethod
  def capture_screenshots(self, output_path: str, file_name_prefix: str):
    """Takes a screenshot of all the displays and saves it to the output path.

    Args:
      output_path: The path to save the screenshots to.
      file_name_prefix: The prefix of the file name to use for the screenshots.
        The display ID will be appended to the file name.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def get_screenshots_path(self) -> str:
    """Returns the path to the screenshots directory on the device."""
    raise NotImplementedError

  @abc.abstractmethod
  def get_temp_dir(self) -> str:
    """Returns the temporary directory on the device."""
    raise NotImplementedError

  @abc.abstractmethod
  def is_powered(self) -> bool:
    """Returns True if the device is receiving power.

    Returns:
      True if the device is receiving power from an external power source or
      power adapter.
    """
    raise NotImplementedError

  def _request_power_on(self):
    """Requests the device to power on via Servo.

    Raises:
      ServoNotConfiguredError: If Servo is not configured.
    """
    if not self._servo:
      raise ServoNotConfiguredError('Failed to request power on device.')
    self._servo.set_power_state(servo_client.PowerState.ON)

  def _request_power_off(self):
    """Requests the device to power off via Servo.

    Raises:
      ServoNotConfiguredError: If Servo is not configured.
    """
    if not self._servo:
      raise ServoNotConfiguredError('Failed to request power off device.')
    self._servo.set_power_state(servo_client.PowerState.OFF)

  def disable_servo_power(self):
    """Requests the device to disable Servo power.

    Raises:
      ServoNotConfiguredError: If Servo is not configured.
    """
    if not self._servo:
      raise ServoNotConfiguredError('Failed to disable Servo power.')
    self._servo.disable_servo_power()
    # make sure device is online after disabling servo power
    self.wait_for_device_online(DEFAULT_WAIT_FOR_DEVICE_ONLINE_TIMEOUT_SECONDS)

  def enable_servo_power(self):
    """Requests the device to enable Servo power.

    Raises:
      ServoNotConfiguredError: If Servo is not configured.
    """
    if not self._servo:
      raise ServoNotConfiguredError('Failed to enable Servo power.')
    self._servo.enable_servo_power()
    # make sure device is online after enabling servo power
    self.wait_for_device_online(DEFAULT_WAIT_FOR_DEVICE_ONLINE_TIMEOUT_SECONDS)
