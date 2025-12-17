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
import enum
import logging
from typing import Any, Callable

from lib.pasit import test_policy
from lib.utils import retry
from lib.utils import servo_client


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


class PasitDeviceError(Exception):
  """Error when performing an action on a PASIT device."""


class BasePasitDevice(metaclass=abc.ABCMeta):
  """Represents a device being tested by PASIT.

  Attributes:
    controller: Mobly controller instance for the tested device.
  """

  class UiApplication(enum.Enum):
    """Represents a UI application on the device."""

    SETTINGS = 'Settings'

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
  def cold_reset(self):
    """Performs a cold reset on the device."""
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
  def is_device_online(self) -> bool:
    """Checks if the device is online."""
    raise NotImplementedError

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
  def wait_app_open(self, app: UiApplication) -> bool:
    """Waits for the UI application to appear.

    Args:
      app: The UI application to wait for.

    Returns:
      True if the UI application appeared, False otherwise.

    Raises:
      ValueError: If the UI application is not supported.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def wait_app_close(self, app: UiApplication) -> bool:
    """Wait for the UI application to close.

    Args:
      app: The UI application to wait for.

    Returns:
      True if the UI application closed, False otherwise.

    Raises:
      ValueError: If the UI application is not supported.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def unexpected_reboots(self) -> bool:
    """Checks if the device has rebooted unexpectedly.

    Returns:
      True if the device has rebooted unexpectedly, False otherwise.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def is_powered(self) -> bool:
    """Returns True if the device is receiving power.

    Returns:
      True if the device is receiving power from an external power source or
      power adapter.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def start_screen_recording(self):
    """Starts screen recording on the device."""
    raise NotImplementedError

  @abc.abstractmethod
  def stop_screen_recording(self, output_path: str):
    """Stops screen recording on the device."""
    raise NotImplementedError

  def wait_for_device_online(self):
    """Waits for the device to be online.

    Raises:
      PasitDeviceError: If the device is not online after the maximum number
      of tries.
    """
    self.wait_for_device_state(
        self.is_device_online,
        'online',
        test_policy.DeviceTestPolicy.WAIT_FOR_DEVICE_ONLINE_RETRY_POLICY,
    )

  def wait_for_device_offline(self):
    """Waits for the device to be offline.

    Raises:
      PasitDeviceError: If the device is not offline after the maximum number
      of tries.
    """
    self.wait_for_device_state(
        self.is_device_offline,
        'offline',
        test_policy.DeviceTestPolicy.WAIT_FOR_DEVICE_OFFLINE_RETRY_POLICY,
    )

  def wait_for_device_state(
      self,
      is_desired_state_func: Callable[[], bool],
      desired_state_name: str,
      policy: retry.RetryPolicy,
  ):
    """Waits for the device to be in the desired state.

    Args:
      is_desired_state_func: The function to check if the device is in the
        desired state.
      desired_state_name: The name of the desired state.
      policy: The retry policy to use for device state checks.

    Raises:
      PasitDeviceError: If the device is not in the desired state after the
      maximum number of tries.
    """
    is_desired_state = retry.retry(
        is_desired_state_func,
        until=lambda is_desired_state: is_desired_state,
        policy=policy,
    )
    if not is_desired_state:
      raise PasitDeviceError(
          f'Device not {desired_state_name} after  {policy.max_tries} tries'
          f' with {policy.delay_seconds} seconds interval.'
      )

  def is_device_offline(self) -> bool:
    """Checks if the device is offline."""
    return not self.is_device_online()

  def power_on_if_offline(self) -> bool:
    """Performs a cold reset on the device to attempt to reconnect it.

    Returns:
      True if device was offline.

    Raises:
      PasitDeviceError: If the device is not online after the cold reset.
    """
    if not self.is_servo_configured():
      logging.debug(
          'Device is not connected to Servo, skipping power on if offline.'
      )
      return self.is_device_offline()

    if not self.is_device_offline():
      logging.debug('Device is online, skipping power on if offline.')
      return False

    logging.warning('Device is offline, performing cold reset...')
    self.cold_reset()
    return True

  def is_servo_configured(self) -> bool:
    """Returns True if Servo is configured."""
    return self._servo is not None

  def disable_servo_power(self):
    """Requests the device to disable Servo power.

    Raises:
      ServoNotConfiguredError: If Servo is not configured.
    """
    if not self._servo:
      raise ServoNotConfiguredError('Failed to disable Servo power.')
    self._servo.disable_servo_power()
    # make sure device is online after disabling servo power
    self.wait_for_device_online()

  def enable_servo_power(self):
    """Requests the device to enable Servo power.

    Raises:
      ServoNotConfiguredError: If Servo is not configured.
    """
    if not self._servo:
      raise ServoNotConfiguredError('Failed to enable Servo power.')
    self._servo.enable_servo_power()
    # make sure device is online after enabling servo power
    self.wait_for_device_online()

  def request_power_on(self):
    """Requests the device to power on via Servo.

    Raises:
      ServoNotConfiguredError: If Servo is not configured.
    """
    if not self._servo:
      raise ServoNotConfiguredError('Failed to request power on device.')
    self._servo.set_power_state(servo_client.PowerState.ON)

  def request_power_off(self):
    """Requests the device to power off via Servo.

    Raises:
      ServoNotConfiguredError: If Servo is not configured.
    """
    if not self._servo:
      raise ServoNotConfiguredError('Failed to request power off device.')
    self._servo.set_power_state(servo_client.PowerState.OFF)

  def set_lid_open(self) -> None:
    """Sets the lid open state of the device via Servo."""
    if not self._servo:
      raise ServoNotConfiguredError('Failed to set lid state to open.')
    self._servo.set_lid_state(True)

  def set_lid_closed(self) -> None:
    """Sets the lid closed state of the device via Servo."""
    if not self._servo:
      raise ServoNotConfiguredError('Failed to set lid state to closed.')
    self._servo.set_lid_state(False)

  def reset(self) -> None:
    """Performs a cold reset, or reboot if servo is not configured.

    Raises:
      PasitDeviceError: If the device is not online after the maximum number
      of tries.
    """
    if not self._servo:
      self.reboot()
      return

    self.cold_reset()

  def safe_reset(self) -> bool:
    """Performs a safe reset, or reboot if servo is not configured.

    Raises no exceptions.

    Returns:
      True if the device was reset successfully, False otherwise.
    """
    try:
      self.reset()
      return True
    except Exception as e:  # pylint: disable=broad-except
      logging.error(
          'Failed to reset device, device may be in a bad state: %s', e
      )
      return False
