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


@enum.unique
class PowerState(str, enum.Enum):
  """Power states for the DUT."""

  ON = 'on'
  OFF = 'off'


class ServoClient:
  """Client for interacting with Servod."""

  def __init__(self, uri: str):
    """Initializes the ServoClient."""
    self._xmlrpc_client = xmlrpc_client.ServerProxy(uri)
    self._verify_connected()

  def _verify_connected(self):
    """Verifies that the client is connected to the Servod."""
    message = 'hello from servo'
    response = self._xmlrpc_client.echo(message)
    if response != f'ECH0ING: {message}':
      raise ConnectionError(
          f'Failed to verify connection to Servod: {response}'
      )

  def set_power_state(self, power_state: PowerState):
    """Sets the power state of the DUT via Servod."""

    value = power_state.value
    response = self._xmlrpc_client.set('power_state', value)
    logging.debug('Set power state to "%s" -> %s', value, response)
