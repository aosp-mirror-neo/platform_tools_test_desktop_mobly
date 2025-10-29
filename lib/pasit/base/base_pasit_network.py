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

"""Interface for interacting with network information on a DUT."""

import abc
import dataclasses
import enum
import json
from typing import Any


class NetworkInfoError(Exception):
  """Raised when there is an error retrieving or parsing network information."""


class NetworkState(enum.Enum):
  """Represents the state of a network device."""

  UNKNOWN = 'UNKNOWN'
  DOWN = 'DOWN'
  UP = 'UP'


@dataclasses.dataclass
class NetworkInfo:
  """Represents information about an Network device.

  name: The name of the network device.
  mac_address: The MAC address of the network device.
  lower_up: Whether the network device is connected at the layer 1 (eg cable
    connected or connected to an AP).
  state: The state of the network device (eg UP, DOWN, UNKNOWN).
  link_type: The type of the network device (eg ether, loopback, etc).
  raw_info: The raw information about the network device from ip link command
    json output.
  """

  name: str
  mac_address: str
  lower_up: bool
  state: NetworkState
  link_type: str
  raw_info: dict[str, Any]


class BasePasitNetwork(metaclass=abc.ABCMeta):
  """Interface for getting network information from a DUT."""

  def __init__(self, controller: Any):
    """Initializes the PasitNetwork class.

    Args:
      controller: The controller to use for accessing the device.
    """
    self.controller = controller

  def get_network_infos_not_down(self) -> dict[str, NetworkInfo]:
    """Gets the network information from the DUT for networks that are not DOWN.

    This is a helper method that filters out the networks that are in DOWN state
    and returns the rest.  The reason for filtering out DOWN and not filtering
    out UP is that some networks show as UNKNOWN even if they are working and
    connected.

    Returns:
      A dictionary of network information, with the network name as the key
      and the NetworkInfo object as the value.
    """
    network_info_dict = self.get_network_infos()
    active_network_info = {}
    for network_info in network_info_dict.values():
      if network_info.state != NetworkState.DOWN:
        active_network_info[network_info.name] = network_info
    return active_network_info

  @abc.abstractmethod
  def get_network_infos(self) -> dict[str, NetworkInfo]:
    """Gets the external storage block device.

    Returns:
      The a dictionary of network information, with the network name as the key
      and the NetworkInfo object as the value.
    Raises:
      NetworkInfoError: If the network information cannot be retrieved or
      parsed.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def is_network_connected_to_internet(self, ifname: str) -> bool:
    """Checks if the network interface is connected to internet.

    Args:
      ifname: The name of the network interface.
    Returns:
      True if the network is connected to internet, False otherwise.
    """
    raise NotImplementedError

  def ip_link_json_to_network_infos(
      self, ip_link_json_str: str
  ) -> dict[str, NetworkInfo]:
    """Converts a JSON output to a dictionary of NetworkInfo object.

    Args:
      ip_link_json_str: The JSON output of the command 'ip -json link show'.

    Returns:
      A dictionary of NetworkInfo object, with the network name as the key and
      the NetworkInfo object as the value.
    Raises:
      NetworkInfoError: If the JSON output is invalid.
    """
    try:
      ip_link_json = json.loads(ip_link_json_str)
    except json.JSONDecodeError as e:
      raise NetworkInfoError(
          'Failed to parse IP link JSON: %s' % ip_link_json_str
      ) from e
    if not isinstance(ip_link_json, list):
      raise NetworkInfoError(
          'Invalid IP Link JSON: IP Link output is not a list.'
      )
    network_info_dict = {}
    for interface_info in ip_link_json:
      operstate = _get_param_from_interface_info(interface_info, 'operstate')
      state = NetworkState.UNKNOWN
      if operstate == 'DOWN':
        state = NetworkState.DOWN
      elif operstate == 'UP':
        state = NetworkState.UP
      flags = _get_param_from_interface_info(interface_info, 'flags')
      ifname = _get_param_from_interface_info(interface_info, 'ifname')
      address = _get_param_from_interface_info(interface_info, 'address')
      link_type = _get_param_from_interface_info(interface_info, 'link_type')
      # ignore loopback, tunnel, etc.
      if link_type != 'ether' or ifname.startswith('dummy'):
        continue
      network_info_dict[ifname] = NetworkInfo(
          name=ifname,
          mac_address=address,
          lower_up='LOWER_UP' in flags,
          state=state,
          link_type=link_type,
          raw_info=interface_info,
      )
    return network_info_dict


def _get_param_from_interface_info(
    interface_info: dict[str, Any], param_name: str
) -> Any:
  """Gets a parameter from the interface info and raises an error if missing.

  Args:
    interface_info: The dictionary containing interface information.
    param_name: The name of the parameter to retrieve.

  Returns:
    The value of the parameter.

  Raises:
    NetworkInfoError: If the parameter is not found in the interface_info.
  """
  param_value = interface_info.get(param_name)
  if not param_value:
    raise NetworkInfoError(
        f'Invalid IP Link JSON: {param_name} is not found in IP Link output'
        ' JSON.'
    )
  return param_value
