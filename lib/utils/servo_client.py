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

"""Client for interacting with Servod."""

import abc
import enum
import logging
import time
import xmlrpc.client as xmlrpc_client
from chromiumos.test.api.bols import bols_service_pb2
from chromiumos.test.api.lsnexus import lsnexus_service_pb2
from chromiumos.test.api.lsnexus import lsnexus_service_pb2_grpc
import grpc


class ServoConnectionError(Exception):
  """Error when trying to connect to Servo."""


ON_STATE = 'on'
OFF_STATE = 'off'

POWER_STATE = 'power_state'
COLD_RESET = 'cold_reset'
BOTTOM_USBKEY_PWR = 'bottom_usbkey_pwr'
TOP_USBKEY_PWR = 'top_usbkey_pwr'

SERVO_PD_ROLE = 'servo_pd_role'
PD_ROLE_SINK = 'snk'
PD_ROLE_SOURCE = 'src'

LID_OPEN = 'lid_open'
EC_UART_CMD = 'ec_uart_cmd'

YES_VALUE = 'yes'
NO_VALUE = 'no'


@enum.unique
class PowerState(str, enum.Enum):
  """Power states for the DUT."""

  ON = ON_STATE
  OFF = OFF_STATE


class ServoBase(abc.ABC):
  """Base class for interacting with Servod"""

  def set_power_state(self, power_state: PowerState):
    """Sets the power state of the DUT via Servod."""
    self._set_servod_value(POWER_STATE, power_state.value)

  def cold_reset(self):
    """Performs a cold reset of the DUT via Servod."""
    self._set_servod_value(COLD_RESET, ON_STATE)
    time.sleep(1)
    self._set_servod_value(COLD_RESET, OFF_STATE)

  def disable_servo_power(self):
    """Disables the Servo power to the DUT."""
    self._set_servod_value(SERVO_PD_ROLE, PD_ROLE_SINK)
    # Wait for the servo to disable power:
    # the pd_role change can cause the DUT to go offline for a brief moment,
    # the sleep allows for that to happen so that waiting for the DUT to
    # come back online doesn't return before the DUT goes offline.
    time.sleep(2)

  def enable_servo_power(self):
    """Enables the Servo power to the DUT."""
    self._set_servod_value(SERVO_PD_ROLE, PD_ROLE_SOURCE)
    # Wait for the servo to enable power:
    # the pd_role change can cause the DUT to go offline for a brief moment,
    # the sleep allows for that to happen so that waiting for the DUT to
    # come back online doesn't return before the DUT goes offline.
    time.sleep(2)

  def set_servo_usbkey_power(self, usbkey_power: bool):
    """Sets the power state of the USB-key via Servod."""
    state = ON_STATE if usbkey_power else OFF_STATE
    self._set_servod_value(BOTTOM_USBKEY_PWR, state)
    self._set_servod_value(TOP_USBKEY_PWR, state)

  def set_lid_state(self, lid_open: bool) -> None:
    """Sets the lid state (open or closed) of the DUT via Servod.

    Args:
      lid_open: True if the lid is open, False if the lid is closed.
    """
    self._set_servod_value(LID_OPEN, YES_VALUE if lid_open else NO_VALUE)

  def set_tablet_mode(self, enabled: bool):
    """Sets the Tablet Mode (On or Off) of the DUT via Servod.

    Args:
      enabled: True for 'tabletmode on', False for 'tabletmode off'
    """
    command = 'tabletmode on' if enabled else 'tabletmode off'
    self._set_servod_value(EC_UART_CMD, command)

  @abc.abstractmethod
  def _set_servod_value(self, name: str, value: str) -> None:
    """Sets the value of a Servod control."""
    raise NotImplementedError

  @abc.abstractmethod
  def verify_connected(self) -> None:
    """Verifies that the client is connected to the Servod.

    Raises:
      ServoConnectionError: If the client is not connected to the Servod.
    """
    raise NotImplementedError


class LSNexusClient(ServoBase):
  """Client for interacting with Servo via LSNexus"""

  def __init__(self, uri: str):
    self._channel = grpc.insecure_channel(uri)
    self._stub = lsnexus_service_pb2_grpc.LSNexusServiceStub(self._channel)
    self._start_servod()
    self.verify_connected()

  def _start_servod(self):
    """Calls StartServod"""
    self._stub.StartServod(
        # Since each test class calls this method it is much more efficient to
        # reuse the existing servod instance, instead of starting a new one.
        lsnexus_service_pb2.StartServodRequest(reuse_existing=True)
    )

  def verify_connected(self):
    """Verifies that the client is connected to the Servod."""
    message = 'hello from lsnexus'
    response = self._stub.Echo(lsnexus_service_pb2.EchoRequest(msg=message))
    if response.result != f'ECH0ING: {message}':
      raise ServoConnectionError(
          f'Failed to verify connection to LSNexus: {response}'
      )

  def get_servo_serial(self) -> str:
    """Gets the serial number of the Servo."""
    request = lsnexus_service_pb2.CallServodRequest(
        method=lsnexus_service_pb2.CallServodRequest.Method.GET,
        control='serialname',
    )
    response = self._call_servod(request)
    return str(response.result.string_value)

  def _set_servod_value(self, name: str, value: str):
    """Sets the value of a Servod control."""
    request = lsnexus_service_pb2.CallServodRequest(
        method=lsnexus_service_pb2.CallServodRequest.Method.SET,
        control=name,
        args=[bols_service_pb2.ServodValue(string_value=value)],
    )
    self._call_servod(request)

  def _call_servod(self, request: lsnexus_service_pb2.CallServodRequest):
    response = self._stub.CallServod(request)
    logging.debug('Call servod %s -> %s', request, response)
    if response.HasField('failure'):
      raise ValueError(response.failure.msg)
    if response.HasField('success'):
      return response.success
    raise ValueError('No response from LSNexus')


class ServodClient(ServoBase):
  """Client for interacting with Servod directly."""

  def __init__(self, uri: str):
    """Initializes the ServoClient."""
    self._xmlrpc_client = xmlrpc_client.ServerProxy(uri)
    self.verify_connected()

  def verify_connected(self):
    """Verifies that the client is connected to the Servod."""
    message = 'hello from servo'
    response = self._xmlrpc_client.echo(message)
    if response != f'ECH0ING: {message}':
      raise ServoConnectionError(
          f'Failed to verify connection to Servod: {response}'
      )

  def _set_servod_value(self, name: str, value: str):
    """Sets the value of a Servod control."""
    response = self._xmlrpc_client.set(name, value)
    logging.debug('Set %s to "%s" -> %s', name, value, response)
