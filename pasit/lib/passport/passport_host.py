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
import enum
import http
import logging
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from google.protobuf import json_format
from mobly import logger as mobly_logger

from pasit.lib.passport import passport_switch_service_client
from pasit.lib.passport import passport_usb_service_client
from chromiumos.test.lab.api import pasit_host_pb2


MOBLY_CONTROLLER_CONFIG_NAME = 'PassportHost'


class PassportBaseError(Exception):
  """Base error class for PassportHost."""


class DevicePathNotFoundError(PassportBaseError):
  """Error when trying to look up the path to a device."""


class PassportServiceConnectionError(PassportBaseError):
  """Error when trying to connect to the Passport API Service."""


class PassportConfigError(PassportBaseError):
  """Error class for the PassportHost controller configuration."""


class PowerState(enum.IntEnum):
  """Power state of a device."""

  ON = 1
  OFF = 0


class PassportIPPowerError(PassportBaseError):
  """Error class for controlling IP power."""

  def __init__(self, message: str, address: str, power_state: PowerState):
    """Initializes the error with a message, address, and power_state state.

    Args:
      message: The error message.
      address: The address of the IP power switch.
      power_state: The state that was attempted to be set.
    """
    super().__init__(message)
    self.message = message
    self.power_state = power_state
    self.address = address

  def __str__(self):
    return (
        f'Failed to set IP power state to {self.power_state.name} for'
        f' {self.address}, verify that the IP Power switch is connected and'
        f' reachable from the test host. {self.message}'
    )


def create(configs: list[dict[str, Any]]) -> list['PassportHost']:
  """Creates Passport device instances."""
  if not configs:
    raise PassportConfigError(f'Missing configuration {configs!r}.')
  if len(configs) > 1:
    raise PassportConfigError(
        f'Multiple PassportHost configs are not supported: {configs!r}'
    )
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
    usb_tester_client: The client for the USB tester service.
  """

  usb_tester_client: passport_usb_service_client.PassportUsbServiceClient = None
  _switch_client: passport_switch_service_client.PassportSwitchServiceClient
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

    service_host = self._config.get('service_host', None)
    service_port = self._config.get('service_port', None)

    if service_host is None and service_port is None:
      # If the service host and port are not set, read from
      # 'switch_service_host'/'switch_service_port' for backwards compatibility.
      service_host = self._config.get('switch_service_host', None)
      service_port = self._config.get('switch_service_port', None)

    if service_host is not None and service_port is not None:
      # If the passport host and port are set, override the hostname in the
      # passport device.
      self.log.info(
          'Overriding hostname "%s" with switch host and port: %s:%s',
          self.topology.hostname,
          service_host,
          service_port,
      )
      self.topology.hostname = f'{service_host}:{service_port}'  # pylint: disable=bad-whitespace

    self.log.info('PassportHost topology: %s' % self.topology)
    self._connect_to_service()
    self._parse_topology()

  def _ensure_passport_connected(self):
    """Ensures the Passport API Service is connected."""
    if not self._switch_client:
      raise PassportServiceConnectionError(
          'Cannot perform operation, Pasport client is not connected.'
      )

  def _connect_to_service(self):
    """Connects to the Passport API Service."""
    if not self.address:
      raise PassportConfigError(
          'PassportHost address is not set, expected to be set in the topology'
          ' or via the service_host and service_port configs.'
      )

    self.log.info('Connecting to Passport API at address: %s' % self.address)
    self._switch_client = (
        passport_switch_service_client.PassportSwitchServiceClient(self.address)
    )
    self.usb_tester_client = (
        passport_usb_service_client.PassportUsbServiceClient(self.address)
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
    devices = self._path_to_device(
        lambda device: device.type == device_type,
        'Passport was unable to find any connections to any devices of type:'
        f' {pasit_host_pb2.PasitHost.Device.Type.Name(device_type)} in the'
        ' topology.',
    )
    return self._connections_in_path(devices)

  def _path_to_device(
      self,
      target_device_fn: Callable[[pasit_host_pb2.PasitHost.Device], bool],
      error_message: str,
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

    raise DevicePathNotFoundError(error_message)

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
    self._ensure_passport_connected()
    connections = self._connections_to_device_by_type(device_type)
    device_path = [connection.parent_id for connection in connections]
    self.log.info(
        f'{"Activating" if enable else "Deactivating"} device by type:'
        f' {pasit_host_pb2.PasitHost.Device.Type.Name(device_type)}, path to'
        f' device: {device_path}',
    )
    device_id = None
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
          self._switch_client.enable_switch(device_id)
        else:
          self._switch_client.disable_switch(device_id)
      elif (
          self._devices[device_id].type
          == pasit_host_pb2.PasitHost.Device.Type.IP_POWER
      ):
        # NOTE: This is a temporary solution to set the IP power state.
        # Once the passport host proto supports a type of IP_POWER, this
        # should be updated to use that type instead.
        self.set_ip_power_state(
            device_id, PowerState.ON if enable else PowerState.OFF
        )

  @property
  def address(self) -> str:
    """Returns the hostname of the PassportHost."""
    return self.topology.hostname

  def reset(self):
    """Resets the PassportHost.

    Raises:
      DevicePathNotFoundError: If the Passport was unable to reset the connected
        switches.
      PassportIPPowerError: If the Passport was unable to reset the IP power
        switches.
    """
    if self._switch_client:
      self._switch_client.reset_all_switches()
    if self.usb_tester_client and self.usb_tester_client.is_open():
      self.usb_tester_client.replug_usb_tester()
    self._reset_ip_power()

  def teardown(self):
    """Tears down the PassportHost."""
    if self._switch_client:
      self._switch_client.close()
      self._switch_client = None

    if self.usb_tester_client and self.usb_tester_client.is_open():
      self.usb_tester_client.close_usb_tester()
      self.usb_tester_client = None

  def activate_device_by_type(
      self, device_type: pasit_host_pb2.PasitHost.Device.Type
  ) -> None:
    """Activates the device with the given device type.

    Args:
      device_type: The device type to activate.

    Raises:
      DevicePathNotFoundError: If the Passport was unable to find the device
        with the given device type.
      PassportIPPowerError: If the Passport was unable to set the IP power
        switch state.
      PassportSwitchError: If the Passport was unable to set the switch state.
    """
    self._set_device_enabled_state_by_type(device_type, True)

  def deactivate_device_by_type(
      self, device_type: pasit_host_pb2.PasitHost.Device.Type
  ) -> None:
    """Deactivates the device with the given device type.

    Args:
      device_type: The device type to deactivate.

    Raises:
      DevicePathNotFoundError: If the Passport was unable to find the device
        with the given device type.
      PassportIPPowerError: If the Passport was unable to set the IP power
        switch state.
      PassportSwitchError: If the Passport was unable to set the switch state.
    """
    self._set_device_enabled_state_by_type(device_type, False)

  def get_switch_ids(self) -> MutableSequence[str]:
    """Returns the switch IDs connected to the PassportHost.

    Raises:
      PassportSwitchClientError: If the Passport was unable to get the switches.
    """
    self._ensure_passport_connected()

    resp = self._switch_client.get_switches()
    return [switch.id for switch in resp.switches]

  def _reset_ip_power(self):
    """Resets all connected IP power switches."""
    for device in self.topology.devices:
      if device.type == pasit_host_pb2.PasitHost.Device.Type.IP_POWER:
        self.set_ip_power_state(device.id, PowerState.OFF)

  def set_ip_power_state(self, address: str, power_state: PowerState) -> None:
    """Sets the IP power switch state through URL request directly from the test.

    Args:
      address: The IP+port of the IP power switch (example: 192.168.1.100:8080).
      power_state: PowerState to set the IP power switch to.

    Raises:
      PassportIPPowerError: If the URL request fails or the response is not as
        expected.
    """
    set_string = f'p61={power_state}'
    url = f'http://{address}/set.cmd?user=admin+pass=12345678+cmd=setpower+{set_string}'

    self.log.debug('Setting IP power state to %s: %s', power_state.name, url)
    try:
      with urllib.request.urlopen(url) as response:
        resp_text = response.read()
        self.log.debug('Response: %s', resp_text)
        if (
            response.status != http.HTTPStatus.OK
            or set_string.encode('utf-8') not in resp_text
        ):
          raise PassportIPPowerError(
              f'Response status: {response.status}, response text: {resp_text}',
              address,
              power_state,
          )
    except (urllib.error.URLError, http.client.BadStatusLine) as e:
      raise PassportIPPowerError(
          'URL request failed.', address, power_state
      ) from e
