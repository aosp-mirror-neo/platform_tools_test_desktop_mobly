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

from pasit.lib.base import servo_client


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


class ServoConnectionError(Exception):
  """Error when trying to connect to Servo."""


class ServoNotConfiguredError(Exception):
  """Error when Servo is not configured."""


class BasePasitDevice(metaclass=abc.ABCMeta):
  """Represents a device being tested by PASIT.

  Attributes:
    controller: Mobly controller instance for the tested device.
  """

  def __init__(self, controller: Any, servo_uri: str):
    """Initializes the PasitDevice.

    Args:
      controller: The controller to use for the PASIT device.
      servo_uri: The URI of Servo. If not empty, the device will be able to
        power cycle.

    Raises:
      ServoConnectionError: If failed to connect to Servo.
    """
    self.controller = controller
    self._servo: servo_client.ServoClient = None

    if servo_uri:
      try:
        self._servo = servo_client.ServoClient(servo_uri)
      except Exception as e:
        raise ServoConnectionError(
            f'Test setup error, failed to connect to Servo at {servo_uri}: {e}'
        ) from e

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
  def suspend(self):
    """Suspends the device."""
    raise NotImplementedError

  @abc.abstractmethod
  def is_device_online(self, timeout: int) -> bool:
    """Checks if the device is online."""
    raise NotImplementedError

  def power_on_if_offline(self, timeout: int = 5) -> bool:
    """Powers on the device if it is offline.

    Args:
      timeout: The timeout in seconds to wait for the device to be online.

    Returns:
      True if device was offline.
    """
    if not self.is_device_online(timeout):
      if self._servo:
        logging.debug('Device is offline, powering on...')
        self.power_on()
      return True
    return False

  def is_servo_configured(self) -> bool:
    """Returns True if Servo is configured."""
    return self._servo is not None

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
