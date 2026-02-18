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

"""Manages the state of a PASIT device."""

import enum
import logging
from lib.pasit import pasit_device
from lib.pasit.base import base_pasit_device


@enum.unique
class PowerState(enum.StrEnum):
  ON = 'on'
  OFF = 'off'
  SUSPEND = 'suspended'


@enum.unique
class PowerAction(enum.StrEnum):
  """Represents power-related actions for the DUT."""

  SUSPEND = 'suspend'
  SHUTDOWN = 'shutdown'
  REBOOT = 'reboot'


def requires_servo(
    state_action: PowerState | PowerAction,
) -> bool:
  """Returns True if servo is required for a dut to enter the given state."""
  return state_action in [
      PowerState.OFF,
      PowerState.SUSPEND,
      PowerAction.SHUTDOWN,
      PowerAction.SUSPEND,
  ]


def execute_power_action(
    dut: pasit_device.PasitDevice,
    action: PowerAction,
    login_on_power_on: bool = True,
):
  """Executes a power transition: shutdown/on, suspend/wakeup, or reboot.

  Args:
    dut: The PASIT device to manage.
    action: The action or state transition to perform.
    login_on_power_on: Whether to log in the device after powering it on.
  """
  if requires_servo(action) and not dut.is_servo_configured():
    raise base_pasit_device.ServoNotConfiguredError(
        f'Servo is not configured, cannot execute {action}.'
    )
  match action:
    case PowerAction.SHUTDOWN:
      logging.info('Powering off device...')
      dut.power_off()
      logging.info('Powering on device...')
      dut.power_on(login=login_on_power_on)

    case PowerAction.SUSPEND:
      logging.info('Suspending device...')
      dut.suspend()
      logging.info('Resuming device...')
      dut.wakeup()

    case PowerAction.REBOOT:
      logging.info('Rebooting device...')
      dut.reboot()


class EnterStateAndReturnToPowerOn:
  """Enter the desired state and return to the power on state.

  The context manager will power on the DUT even if there is an exception
  raised or the test fails during the context execution. Any exceptions raised
  during the context execution will be re-raised.
  """

  def __init__(
      self,
      dut: pasit_device.PasitDevice,
      desired_state: PowerState,
      login_on_power_on: bool = True,
  ):
    """Initializes the context manager based on the DUT and desired state.

    Args:
      dut: The PASIT device to manage.
      desired_state: The desired state to enter.
      login_on_power_on: Whether to log in the device after powering it on.
    """
    self._dut = dut
    self._desired_state = desired_state
    self._login_on_power_on = login_on_power_on

  def __enter__(self):
    if (
        requires_servo(self._desired_state)
        and not self._dut.is_servo_configured()
    ):
      raise base_pasit_device.ServoNotConfiguredError(
          'Servo is not configured, cannot change dut state.'
      )

    if self._desired_state == PowerState.OFF:
      logging.info('Powering off DUT')
      self._dut.power_off()
    elif self._desired_state == PowerState.SUSPEND:
      logging.info('Suspending DUT')
      self._dut.suspend()

  def __exit__(self, exc_type, exc_val, exc_tb):
    if self._desired_state == PowerState.OFF:
      logging.info('Powering on DUT')
      self._dut.power_on(login=self._login_on_power_on)
    elif self._desired_state == PowerState.SUSPEND:
      logging.info('Waking up DUT from suspend')
      self._dut.wakeup()
    return False
