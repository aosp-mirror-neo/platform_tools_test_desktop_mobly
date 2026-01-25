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

"""A test that exercises PASIT HID functionality."""

import logging

from lib.pasit import network_helper
from lib.pasit import pasit_network
from lib.pasit import pasit_test
from mobly import asserts
from mobly import test_runner


class PasitNetworkTest(pasit_test.PasitTestClass):
  """A test that exercises PASIT Network functionality."""

  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_NETWORK

  def setup_class(self) -> None:
    super().setup_class()
    self.network = self.create(pasit_network)
    self.helper = network_helper.NetworkHelper(self.network)

  def setup_test(self) -> None:
    super().setup_test()
    networks_before = self.network.get_network_infos()
    self.plug_in_network_device()
    new_networks = self.helper.wait_for_new_network_detected(networks_before)
    asserts.assert_equal(
        len(new_networks),
        1,
        'Expected exactly one new network device to be detected after'
        f' activation, but got got {len(new_networks)}.',
    )

  def teardown_class(self) -> None:
    super().teardown_class()
    # network cleanup should be called after passport reset
    # in super().teardown_class()
    if hasattr(self, 'network'):
      self.network.cleanup()

  def test_get_network_infos(self) -> None:
    networks = self.network.get_network_infos()
    asserts.assert_true(
        networks, 'Expected at least one network from get_network_infos'
    )
    for network in networks.values():
      logging.info('Checking network: %s', network.name)
      logging.debug('network: %s', network)
      asserts.assert_true(
          network.mac_address,
          f'Expected network {network.name} mac_address to be not empty, got:'
          f' {network.mac_address}',
      )
      asserts.assert_true(
          network.state,
          f'Expected network {network.name} state to be not empty, got:'
          f' {network.state}',
      )
      asserts.assert_true(
          network.link_type,
          f'Expected network {network.name} link_type to be not empty, got:'
          f' {network.link_type}',
      )
      asserts.assert_true(
          network.raw_info,
          f'Expected network {network.name} raw_info to be not empty, got:'
          f' {network.raw_info}',
      )

  def test_get_network_infos_not_down(self) -> None:
    networks = self.helper.wait_for_any_not_down_network()
    asserts.assert_true(
        networks,
        'Expected at least one network from get_network_infos_not_down',
    )

    found_lower_up_iface = ''
    for network in networks.values():
      logging.info('Found network: %s', network.name)
      logging.debug('network: %s', network)
      asserts.assert_not_equal(
          network.state,
          pasit_network.NetworkState.DOWN,
          f'Expected network {network.name} state to be not DOWN, got:'
          f' {network.state}',
      )
      if network.lower_up:
        found_lower_up_iface = network.name
    asserts.assert_true(
        found_lower_up_iface, 'Expected at least one network with lower_up True'
    )
    logging.info('Found network with lower_up True: %s', found_lower_up_iface)

  def test_is_network_connected_to_internet(self) -> None:
    networks = self.helper.wait_for_any_not_down_network()
    asserts.assert_true(
        networks,
        'Expected at least one network from get_network_infos_not_down',
    )
    # try the connected test on the first network found that is not DOWN
    iface = next(iter(networks.values()))
    logging.info(
        'Found network that is not DOWN: %s, checking if connected to internet',
        iface.name,
    )
    asserts.assert_true(
        self.network.is_network_connected_to_internet(iface.name),
        f'Expected network {iface.name} to be connected to internet',
    )

  def test_is_network_connected_to_internet_not_connected(self) -> None:
    networks = self.network.get_network_infos()
    asserts.assert_true(
        networks, 'Expected at least one network from get_network_infos'
    )

    iface = None
    # try the connected test on the first network found that is not DOWN
    for network in networks.values():
      if network.state != pasit_network.NetworkState.DOWN:
        continue
      iface = network
      break
    asserts.assert_true(
        iface, 'Expected at least one network that is DOWN to be found'
    )
    if iface is None:
      return
    logging.info(
        'Found network that is DOWN: %s, checking if connected to internet'
        ' fails',
        iface.name,
    )
    asserts.assert_false(
        self.network.is_network_connected_to_internet(iface.name),
        f'Expected network {iface.name} to be not connected to internet',
    )

  def plug_in_network_device(self) -> None:
    """Plugs in the network device to the DUT."""
    logging.info('Plugging in network device to DUT')
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_NETWORK)


if __name__ == '__main__':
  test_runner.main()
