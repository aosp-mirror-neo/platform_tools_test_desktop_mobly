# Copyright 2026 Google LLC
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

"""Helper class for network operations."""

import logging

from lib.pasit import pasit_network
from lib.pasit import test_policy
from lib.utils import retry


class NetworkHelper:
  """Helper class for network operations."""

  network: pasit_network.PasitNetwork

  def __init__(self, network: pasit_network.PasitNetwork):
    self.network = network

  def wait_for_new_network_detected(
      self, networks: dict[str, pasit_network.NetworkInfo]
  ) -> dict[str, pasit_network.NetworkInfo]:
    """Waits for a new network to be detected.

    Args:
      networks: The network devices before activation.

    Returns:
      The newly detected network devices.
    """

    logging.info('Waiting for new network device to be detected...')
    new_networks = retry.retry(
        self.network.get_network_infos,
        until=lambda new_networks: new_networks.keys() - networks.keys(),
        policy=test_policy.NetworkTestPolicy.DETECT_EXTERNAL_NETWORK_DEVICES_RETRY_POLICY,
    )
    return {k: v for k, v in new_networks.items() if k not in networks}

  def wait_for_any_not_down_network(
      self,
  ) -> dict[str, pasit_network.NetworkInfo]:
    """Waits for any not down network to be detected.

    Returns:
      The network devices that are not down.
    """
    logging.info('Waiting for any not down network device to be detected...')
    return retry.retry(
        self.network.get_network_infos_not_down,
        until=lambda networks: networks,
        policy=test_policy.NetworkTestPolicy.DETECT_EXTERNAL_NETWORK_DEVICES_RETRY_POLICY,
    )

  def wait_for_network_cable_connected(self, iface_name: str) -> bool:
    """Waits for the network cable to be connected.

    Args:
      iface_name: The name of the network interface.

    Returns:
      True if the network cable is connected, False otherwise.
    """
    logging.info('Waiting for network cable to be connected...')
    networks = retry.retry(
        self.network.get_network_infos,
        until=lambda networks: self._is_network_cable_connected(
            networks, iface_name
        ),
        policy=test_policy.NetworkTestPolicy.DETECT_NETWORK_CABLE_CONNECTED_RETRY_POLICY,
    )
    return self._is_network_cable_connected(networks, iface_name)

  def wait_for_network_connected_to_internet(self, iface_name: str) -> bool:
    """Waits for the network to be connected to the internet.

    Args:
      iface_name: The name of the network interface.

    Returns:
      True if the network is connected to the internet, False otherwise.
    """
    logging.info(
        'Waiting for network %s to be connected to the internet...', iface_name
    )
    return retry.retry(
        lambda: self.network.is_network_connected_to_internet(iface_name),
        until=lambda result: result,
        policy=test_policy.NetworkTestPolicy.DETECT_NETWORK_INTERNET_CONNECTED_RETRY_POLICY,
    )

  def _is_network_cable_connected(
      self, networks: dict[str, pasit_network.NetworkInfo], iface_name: str
  ) -> bool:
    """Checks if the network cable is connected."""
    if iface_name not in networks:
      return False
    return networks[iface_name].lower_up
