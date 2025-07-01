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

import enum
import logging
import xmlrpc.client as xmlrpc_client

import abc
import grpc

from chromiumos.test.api.bols import bols_service_pb2
from chromiumos.test.api.lsnexus import lsnexus_service_pb2
from chromiumos.test.api.lsnexus import lsnexus_service_pb2_grpc

class ServoConnectionError(Exception):
  """Error when trying to connect to Servo."""


@enum.unique
class PowerState(str, enum.Enum):
  """Power states for the DUT."""

  ON = 'on'
  OFF = 'off'


class ServoBase(abc.ABC):
  """Base class for interacting with Servod"""

  @abc.abstractmethod
  def set_power_state(self, power_state: PowerState):
    """Sets the power state of the DUT via Servod."""
    pass


class LSNexusClient(ServoBase):
  """Client for interacting with Servo via LSNexus"""

  def __init__(self, uri: str):
    self._channel = grpc.insecure_channel(uri)
    self._stub = lsnexus_service_pb2_grpc.LSNexusServiceStub(self._channel)
    self._start_servod()
    self._verify_connected()

  def _start_servod(self):
    """Calls StartServod"""
    self._stub.StartServod(lsnexus_service_pb2.StartServodRequest())

  def _verify_connected(self):
    """Verifies that the client is connected to the Servod."""
    message = 'hello from lsnexus'
    response = self._stub.Echo(
      lsnexus_service_pb2.EchoRequest(msg = message)
    )
    if response.result != f'ECH0ING: {message}':
      raise ServoConnectionError(
          f'Failed to verify connection to LSNexus: {response}'
      )

  def set_power_state(self, power_state: PowerState):
    """Sets the power state of the DUT via Servod."""
    request = lsnexus_service_pb2.CallServodRequest(
        method = lsnexus_service_pb2.CallServodRequest.Method.SET,
        control = "power_state",
        args = [bols_service_pb2.ServodValue(string_value = power_state.value)],
      )
    self._call_servod(request)

  def _call_servod(self, request: lsnexus_service_pb2.CallServodRequest):
    response = self._stub.CallServod(request)
    if response.HasField("failure"):
      raise ValueError(response.failure.msg)
    return response.Success


class ServodClient(ServoBase):
  """Client for interacting with Servod directly."""

  def __init__(self, uri: str):
    """Initializes the ServoClient."""
    self._xmlrpc_client = xmlrpc_client.ServerProxy(uri)
    self._verify_connected()

  def _verify_connected(self):
    """Verifies that the client is connected to the Servod."""
    message = 'hello from servo'
    response = self._xmlrpc_client.echo(message)
    if response != f'ECH0ING: {message}':
      raise ServoConnectionError(
          f'Failed to verify connection to Servod: {response}'
      )

  def set_power_state(self, power_state: PowerState):
    """Sets the power state of the DUT via Servod."""

    value = power_state.value
    response = self._xmlrpc_client.set('power_state', value)
    logging.debug('Set power state to "%s" -> %s', value, response)
