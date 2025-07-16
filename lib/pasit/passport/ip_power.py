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

"""Code for controlling IP power switches for PASIT."""

import enum
from typing import Any

from lib.pasit.passport import errors


class PowerState(enum.IntEnum):
  """Power state of a device."""

  ON = 1
  OFF = 0

  @classmethod
  def from_bool(cls, value: bool):
    """Creates a PowerState enum member from a boolean value.

    Args:
      value: True for ON, False for OFF.
    Returns:
      A PowerState enum member (ON or OFF).
    """
    if value:
      return cls.ON
    else:
      return cls.OFF


class PassportRPMError(errors.PassportBaseError):
  """Error class for Remote Power Management (RPM)."""

  def __init__(self, message: str, endpoint: str, power_state: PowerState):
    """Initializes the error with a message, address, and power_state state.

    Args:
      message: The error message.
      endpoint: The endpoint for the power switch, in the format
        hostname:port.
      power_state: The state that was attempted to be set.
    """
    super().__init__(message)
    self.message = message
    self.endpoint = endpoint
    self.power_state = power_state

  def __str__(self):
    return (
        f'Failed to set IP power state to {self.power_state.name} for'
        f' {self.endpoint}, verify that the IP Power switch is connected and'
        f' reachable from the test host. {self.message}'
    )


class PassportRPM:
  """A class for controlling IP power switches for PASIT."""

  power_unit_endpoint: str
  power_unit_outlet: str

  def __init__(self, endpoint: str, outlet: str):
    """Initializes the IP power switch.

    Args:
      endpoint: The endpoint of the IP power switch, this can be an IP address
        or hostname and can optionally include a port using the format
        hostname:port.
      outlet: The outlet of the IP power switch. (Example '1', '2', '3', etc.)

    """
    self.power_unit_endpoint = endpoint
    self.power_unit_outlet = outlet

  def is_online(self) -> bool:
    """Returns True if the IP power switch is online."""
    raise NotImplementedError

  def set_ip_power_state(self, power_state: PowerState) -> None:
    """Sets the IP power switch state through URL request directly from the test.

    Args:
      power_state: PowerState to set the IP power switch to.

    Raises:
      PassportRPMError: If the URL request fails or the response
        is not as expected.
    """
    raise NotImplementedError
