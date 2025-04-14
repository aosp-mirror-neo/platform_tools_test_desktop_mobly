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

"""Controller for interacting with PASIT testbed via a Passport API Host."""

from collections.abc import Callable, MutableSequence, Sequence
import http
import logging
from typing import Any
import urllib.error
import urllib.parse
import urllib.request


from google.protobuf import json_format
from mobly import logger as mobly_logger

from pasit.lib.passport import passport_switch_service_client
from chromiumos.test.lab.api import pasit_host_pb2


MOBLY_CONTROLLER_CONFIG_NAME = 'PassportHost'


class Error(Exception):
  """Error class for the PassportHost controller."""


def create(configs: list[dict[str, Any]]) -> list['PassportHost']:
  """Creates Passport device instances."""
  if not configs:
    raise Error(f'Missing configuration {configs!r}.')
  if len(configs) > 1:
    raise Error(f'Multiple PassportHost configs are not supported: {configs!r}')
  return [PassportHost(config) for config in configs]


def destroy(devices: list['PassportHost']) -> None:
  """Closes all created Passport device instances."""
  for device in devices:
    try:
      device.teardown()
    except Exception:  # pylint: disable=broad-except
      logging.exception('Failed to clean up properly.')


class PassportHost:
  """A device that hosts a PassportHost API.

  Attributes:
    topology: The topology of the Pasit Testbed.
    address: The address of the PassportHost (in the form of hostname:port).
    log: The logger for the PassportHost.
  """

  _client = None
  _dut_id = None
  _devices: dict[str, pasit_host_pb2.PasitHost.Device] = {}
  _connections: dict[
      str, MutableSequence[pasit_host_pb2.PasitHost.Connection]
  ] = {}

  def __init__(self, config):
    self._config = config
    self.log = mobly_logger.PrefixLoggerAdapter(
        logging.getLogger(),
        {
            mobly_logger.PrefixLoggerAdapter.EXTRA_KEY_LOG_PREFIX: (
                f'[{MOBLY_CONTROLLER_CONFIG_NAME}]'
            )
        },
    )

    topology = self._config.get('host_topology', None)
    if topology is None:
      # If no topology is found, that's fine. The test will need to manage the
      # switch IDs directly.
      self.log.info('No topology found, creating empty topology.')
      self.topology = pasit_host_pb2.PasitHost()
    else:
      self.topology = json_format.ParseDict(
          topology, pasit_host_pb2.PasitHost()
      )

    switch_host = self._config.get('switch_service_host', None)
    switch_port = self._config.get('switch_service_port', None)
    if switch_host is not None and switch_port is not None:
      # If the switch host and port are set, override the hostname in the
      # passport device.
      self.log.info(
          'Overriding hostname "%s" with switch host and port: %s:%s',
          self.topology.hostname,
          switch_host,
          switch_port,
      )
      self.topology.hostname = f'{switch_host}:{switch_port}'

    self.log.info('PassportHost topology: %s' % self.topology)
    self._connect_to_service()
    self._parse_topology()

  def _connect_to_service(self):
    """Connects to the Passport API Service."""
    if not self.address:
      raise Error(
          'PassportHost address is not set, expected to be set in the topology'
          ' or via the switch_service_host and switch_service_port configs.'
      )

    host_info = urllib.parse.urlsplit('//' + self.address)
    self.log.info(
        'Connecting to Passport API at host: %s, port: %s'
        % (host_info.hostname, host_info.port)
    )
    self._client = passport_switch_service_client.PassportSwitchServiceClient(
        host_info.hostname, host_info.port
    )

  def _parse_topology(self):
    """Parses the topology and stores the devices and connections."""
    for device in self.topology.devices:
      self._devices[device.id] = device
      if device.type == pasit_host_pb2.PasitHost.Device.Type.DUT:
        self._dut_id = device.id
    for connection in self.topology.connections:
      for key in [connection.parent_id, connection.child_id]:
        if key in self._connections:
          self._connections[key].append(connection)
        else:
          self._connections[key] = [connection]

  def _connections_to_device_by_type(
      self, device_type: pasit_host_pb2.PasitHost.Device.Type
  ) -> MutableSequence[pasit_host_pb2.PasitHost.Connection]:
    """Returns the path to the device with the given device type."""
    devices = self._path_to_device(lambda device: device.type == device_type)
    return self._connections_in_path(devices)

  def _path_to_device(
      self, target_device_fn: Callable[[pasit_host_pb2.PasitHost.Device], bool]
  ) -> MutableSequence[str]:
    """Returns the path to the device that matches the given function."""
    current_path = []
    stack = [self._dut_id]
    visited: dict[str, bool] = {self._dut_id: True}
    children: dict[str, int] = {}

    while stack:
      current = stack.pop()
      current_path.append(current)

      if target_device_fn(self._devices[current]):
        return current_path

      for node in self._connections[current]:
        if visited.get(node.child_id, False):
          continue
        stack.append(node.child_id)
        visited[node.child_id] = True
        children.setdefault(current, 0)
        children[current] += 1

      while len(current_path) > 1 and children.get(current, 0) == 0:
        current_path.pop()
        current = current_path[-1]
        children.setdefault(current, 0)
        children[current] -= 1

    raise Error('No device found')

  def _connections_in_path(
      self, path: Sequence[str]
  ) -> MutableSequence[pasit_host_pb2.PasitHost.Connection]:
    """Returns the connections in the given path."""
    connections = []
    for i in range(len(path) - 1):
      parent_id = path[i]
      child_id = path[i + 1]
      for connection in self._connections[parent_id]:
        if child_id == connection.child_id:
          connections.append(connection)
          break
    return connections

  def _set_device_enabled_state_by_type(
      self, device_type: pasit_host_pb2.PasitHost.Device.Type, enable: bool
  ) -> None:
    """Activates or deactivates the device with the given device type."""
    if not self._client:
      raise Error('Client is not connected.')

    connections = self._connections_to_device_by_type(device_type)
    device_path = [connection.parent_id for connection in connections]
    self.log.info(
        f'{"Activating" if enable else "Deactivating"} device by type:'
        f' {pasit_host_pb2.PasitHost.Device.Type.Name(device_type)}, path to'
        f' device: {device_path}',
    )

    for device_id in device_path:
      if (
          self._devices[device_id].type
          == pasit_host_pb2.PasitHost.Device.Type.SWITCH_FIXTURE
      ):
        self.log.debug(
            'Setting switch %s to %s',
            device_id,
            'enabled' if enable else 'disabled',
        )
        if enable:
          self._client.enable_switch(device_id)
        else:
          self._client.disable_switch(device_id)
      elif (
          self._devices[device_id].type
          == pasit_host_pb2.PasitHost.Device.Type.IP_POWER
      ):
        # NOTE: This is a temporary solution to set the IP power state.
        # Once the passport host proto supports a type of IP_POWER, this should
        # be updated to use that type instead.
        self.set_ip_power_state(device_id, enable)

  @property
  def address(self) -> str:
    """Returns the hostname of the PassportHost."""
    return self.topology.hostname

  def reset(self):
    """Resets the PassportHost."""
    if self._client:
      self._client.reset_all_switches()
    self._reset_ip_power()

  def teardown(self):
    """Tears down the PassportHost."""
    if self._client:
      self._client.close()
      self._client = None

  def activate_device_by_type(
      self, device_type: pasit_host_pb2.PasitHost.Device.Type
  ) -> None:
    """Activates the device with the given device type."""
    self._set_device_enabled_state_by_type(device_type, True)

  def deactivate_device_by_type(
      self, device_type: pasit_host_pb2.PasitHost.Device.Type
  ) -> None:
    """Deactivates the device with the given device type."""
    self._set_device_enabled_state_by_type(device_type, False)

  def get_switch_ids(self) -> MutableSequence[str]:
    """Returns the switch IDs connected to the PassportHost."""
    if not self._client:
      raise Error('Client is not connected.')

    resp = self._client.get_switches()
    return [switch.id for switch in resp.switches]

  def _reset_ip_power(self):
    """Resets all connected IP power switches."""
    for device in self.topology.devices:
      if device.type == pasit_host_pb2.PasitHost.Device.Type.IP_POWER:
        self.set_ip_power_state(device.id, False)

  def set_ip_power_state(self, ip_port: str, enable: bool) -> None:
    """Sets the IP power switch state through URL request directly from the test.

    Args:
      ip_port: The IP+port of the IP power switch (example: 192.168.1.100:8080).
      enable: True to power on the IP power switch, False to power off.

    Raises:
      Error: If the URL request fails.
    """
    state = '1' if enable else '0'
    url = (
        f'http://{ip_port}/set.cmd?user=admin+pass=12345678+cmd=setpower+p61={state}'
    )
    err_msg = (
        f'Failed to set ip power state to {enable} for {ip_port}, verify that'
        ' the IP Power switch is connected and reachable from the test host.'
    )
    self.log.debug('Setting ip power state to %s: %s', enable, url)
    try:
      with urllib.request.urlopen(url) as response:
        resp_text = response.read()
        self.log.debug('Response: %s', resp_text)
        if response.status != http.HTTPStatus.OK:
          raise Error(
              err_msg
              + f'\tResponse status: {response.status}, response text:'
              f' {resp_text}'
          )
    except urllib.error.URLError as e:
      raise Error(err_msg + f'\n\t{e}') from e
