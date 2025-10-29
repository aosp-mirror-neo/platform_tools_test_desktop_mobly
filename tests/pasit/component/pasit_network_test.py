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
    networks = self.network.get_network_infos_not_down()
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


if __name__ == '__main__':
  test_runner.main()
