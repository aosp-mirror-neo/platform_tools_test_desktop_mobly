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

"""Unit tests for android_pasit_network."""

import unittest
from unittest import mock
from lib.pasit.android import android_pasit_network
from lib.pasit.base import base_pasit_network


class AndroidPasitNetworkTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self.mock_controller = mock.MagicMock()
    # Mocking __init__ call because it calls _start_ehide
    with mock.patch.object(
        android_pasit_network.AndroidPasitNetwork, '_start_ehide'
    ):
      self.network = android_pasit_network.AndroidPasitNetwork(
          self.mock_controller
      )

  def test_start_ehide_success(self):
    with mock.patch.object(
        self.network, '_get_servo_mac', return_value='00:11:22:33:44:55'
    ):
      self.mock_controller.adb.shell.return_value = b'running'
      self.network._start_ehide()

    # Check if correct properties were set
    calls = self.mock_controller.adb.shell.call_args_list
    setprop_hwaddr = mock.call(
        ['setprop', self.network.HWADDR_ALLOWLIST_PROPERTY, '00:11:22:33:44:55']
    )
    setprop_autostart = mock.call(
        ['setprop', self.network.AUTOSTART_EHIDE_PROPERTY, '1']
    )
    self.assertIn(setprop_hwaddr, calls)
    self.assertIn(setprop_autostart, calls)

  def test_get_servo_mac_success(self):
    # Mock get_network_infos to return one Ethernet interface
    mock_info = mock.MagicMock(spec=base_pasit_network.NetworkInfo)
    mock_info.link_type = 'ether'
    mock_info.state = base_pasit_network.NetworkState.UP
    mock_info.lower_up = True
    mock_info.mac_address = '00:11:22:33:44:55'

    with mock.patch.object(
        self.network, 'get_network_infos', return_value={'eth0': mock_info}
    ):
      mac = self.network._get_servo_mac()
    self.assertEqual(mac, '00:11:22:33:44:55')

  def test_get_servo_mac_multiple_ether_only_one_active_success(self):
    # Mock get_network_infos to return multiple 'ether' interfaces but only one
    # UP and lower_up, similar to the real DUT case provided by user
    eth0 = mock.MagicMock(spec=base_pasit_network.NetworkInfo)
    eth0.link_type = 'ether'
    eth0.state = base_pasit_network.NetworkState.UP
    eth0.lower_up = True
    eth0.mac_address = '88:54:1f:0f:84:8b'

    ifb0 = mock.MagicMock(spec=base_pasit_network.NetworkInfo)
    ifb0.link_type = 'ether'
    ifb0.state = base_pasit_network.NetworkState.DOWN
    ifb0.lower_up = False

    wlan0 = mock.MagicMock(spec=base_pasit_network.NetworkInfo)
    wlan0.link_type = 'ether'
    wlan0.state = base_pasit_network.NetworkState.DOWN
    wlan0.lower_up = False

    with mock.patch.object(
        self.network,
        'get_network_infos',
        return_value={'eth0': eth0, 'ifb0': ifb0, 'wlan0': wlan0},
    ):
      mac = self.network._get_servo_mac()
    self.assertEqual(mac, '88:54:1f:0f:84:8b')

  def test_get_servo_mac_no_ethernet_fails(self):
    # Mock get_network_infos to return no Ethernet interfaces that are
    # UP/lower_up
    mock_info = mock.MagicMock(spec=base_pasit_network.NetworkInfo)
    mock_info.link_type = 'ether'
    mock_info.state = base_pasit_network.NetworkState.DOWN
    mock_info.lower_up = False

    with mock.patch.object(
        self.network, 'get_network_infos', return_value={'eth0': mock_info}
    ):
      with self.assertRaisesRegex(
          base_pasit_network.NetworkInfoError, 'No Ethernet interface found'
      ):
        self.network._get_servo_mac()

  def test_get_servo_mac_multiple_active_ethernet_fails(self):
    # Mock get_network_infos to return multiple Ethernet interfaces that are
    # UP/lower_up
    mock_info1 = mock.MagicMock(spec=base_pasit_network.NetworkInfo)
    mock_info1.link_type = 'ether'
    mock_info1.state = base_pasit_network.NetworkState.UP
    mock_info1.lower_up = True

    mock_info2 = mock.MagicMock(spec=base_pasit_network.NetworkInfo)
    mock_info2.link_type = 'ether'
    mock_info2.state = base_pasit_network.NetworkState.UP
    mock_info2.lower_up = True

    with mock.patch.object(
        self.network,
        'get_network_infos',
        return_value={'eth0': mock_info1, 'eth1': mock_info2},
    ):
      with self.assertRaisesRegex(
          base_pasit_network.NetworkInfoError,
          'Multiple Ethernet interfaces found',
      ):
        self.network._get_servo_mac()


if __name__ == '__main__':
  unittest.main()
