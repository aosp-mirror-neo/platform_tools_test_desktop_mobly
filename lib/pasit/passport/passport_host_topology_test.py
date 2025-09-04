# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
from unittest import mock

from chromiumos.test.lab.api import pasit_host_pb2
from lib.pasit.passport import passport_host

TEST_TOPOLOGY = {
    'simple': {
        'hostname': 'dut-12345',
        'devices': [
            {'id': 'dut-12345', 'type': 'DUT'},
            {'id': 'switch1', 'type': 'SWITCH_FIXTURE'},
            {'id': 'switch2', 'type': 'SWITCH_FIXTURE'},
            {'id': 'camera1', 'type': 'CAMERA'},
            {'id': 'monitor1', 'type': 'MONITOR'},
        ],
        'connections': [
            {
                'parent_id': 'dut-12345',
                'child_id': 'switch1',
            },
            {
                'parent_id': 'switch1',
                'child_id': 'monitor1',
            },
            {
                'parent_id': 'dut-12345',
                'child_id': 'switch2',
            },
            {
                'parent_id': 'switch2',
                'child_id': 'camera1',
            },
        ],
    },
    'pasit-box': {
        'hostname': 'dut-23456',
        'devices': [
            {
                'id': 'dut-23456',
                'type': 'DUT',
            },
            {'id': '2209501', 'type': 'SWITCH_FIXTURE'},
            {'id': 'dock_1', 'type': 'DOCKING_STATION'},
            {'id': '2007901', 'type': 'SWITCH_FIXTURE'},
            {'id': 'monitor_1', 'type': 'MONITOR'},
            {'id': '2007902', 'type': 'SWITCH_FIXTURE'},
            {'id': 'monitor_2', 'type': 'MONITOR'},
            {'id': '2001901', 'type': 'SWITCH_FIXTURE'},
            {'id': 'storage_1', 'type': 'STORAGE'},
            {'id': 'j45sw01', 'type': 'SWITCH_FIXTURE'},
            {'id': 'network_1', 'type': 'NETWORK'},
            {'id': '2001902', 'type': 'SWITCH_FIXTURE'},
            {'id': 'storage_2', 'type': 'STORAGE'},
            {'id': '2001903', 'type': 'SWITCH_FIXTURE'},
            {'id': 'camera_1', 'type': 'CAMERA'},
            {'id': '2001904', 'type': 'SWITCH_FIXTURE'},
            {'id': 'hid_1', 'type': 'HID'},
            {'id': '2109002', 'type': 'SWITCH_FIXTURE'},
        ],
        'connections': [
            {
                'parent_id': 'dut-23456',
                'child_id': '2209501',
                'tags': ['DOCK', 'DOCKLESS', 'DAISY_CHAIN'],
            },
            {
                'parent_port': 'A',
                'parent_id': '2209501',
                'child_id': 'dock_1',
                'tags': ['DOCK'],
            },
            {'parent_id': 'dock_1', 'child_id': '2007901', 'tags': ['DOCK']},
            {'parent_id': '2007901', 'child_id': 'monitor_1', 'tags': ['DOCK']},
            {'parent_id': 'dock_1', 'child_id': '2007902', 'tags': ['DOCK']},
            {'parent_id': '2007902', 'child_id': 'monitor_2', 'tags': ['DOCK']},
            {'parent_id': 'dock_1', 'child_id': '2001901', 'tags': ['DOCK']},
            {'parent_id': '2001901', 'child_id': 'storage_1', 'tags': ['DOCK']},
            {'parent_id': 'dock_1', 'child_id': 'j45sw01', 'tags': ['DOCK']},
            {'parent_id': 'j45sw01', 'child_id': 'network_1', 'tags': ['DOCK']},
            {
                'parent_id': 'dut-23456',
                'child_id': '2001902',
                'tags': ['DOCKLESS'],
            },
            {
                'parent_id': '2001902',
                'child_id': 'storage_2',
                'tags': ['DOCKLESS'],
            },
            {
                'parent_id': 'dut-23456',
                'child_id': '2001903',
                'tags': ['DOCKLESS'],
            },
            {
                'parent_id': '2001903',
                'child_id': 'camera_1',
                'tags': ['DOCKLESS'],
            },
            {
                'parent_id': 'dut-23456',
                'child_id': '2001904',
                'tags': ['DOCKLESS'],
            },
            {'parent_id': '2001904', 'child_id': 'hid_1', 'tags': ['DOCKLESS']},
            {
                'parent_port': 'B',
                'parent_id': '2209501',
                'child_id': 'monitor_1',
                'tags': ['DOCKLESS', 'DAISY_CHAIN'],
            },
            {
                'parent_id': 'monitor_1',
                'child_id': '2109002',
                'tags': ['DAISY_CHAIN'],
            },
            {
                'parent_id': '2109002',
                'child_id': 'monitor_2',
                'tags': ['DAISY_CHAIN'],
            },
        ],
    },
    'pasit-full': {
        'hostname': 'dut-34567',
        'devices': [
            {'id': 'dut-34567', 'type': 'DUT'},
            {'id': '1912901', 'type': 'SWITCH_FIXTURE'},
            {'id': 'dock_1', 'type': 'DOCKING_STATION'},
            {'id': '2007901', 'type': 'SWITCH_FIXTURE'},
            {'id': 'monitor_1', 'type': 'MONITOR'},
            {'id': '2109002', 'type': 'SWITCH_FIXTURE'},
            {'id': 'monitor_2', 'type': 'MONITOR'},
            {'id': 'j45sw01', 'type': 'SWITCH_FIXTURE'},
            {'id': 'network_1', 'type': 'NETWORK'},
            {'id': '2001901', 'type': 'SWITCH_FIXTURE'},
            {'id': 'storage_1', 'type': 'STORAGE'},
        ],
        'connections': [
            {'parent_id': 'dut-34567', 'child_id': '1912901'},
            {'parent_id': '1912901', 'child_id': 'dock_1'},
            {'parent_id': 'dock_1', 'child_id': '2109002'},
            {'parent_id': '2109002', 'child_id': 'monitor_2', 'tags': ['EDID']},
            {'parent_id': '2007901', 'child_id': 'monitor_1'},
            {'parent_id': 'dock_1', 'child_id': '2007901'},
            {'parent_id': 'dock_1', 'child_id': 'j45sw01'},
            {'parent_id': 'j45sw01', 'child_id': 'network_1'},
            {'parent_id': 'dock_1', 'child_id': '2001901'},
            {'parent_id': '2001901', 'child_id': 'storage_1'},
        ],
    },
}


class PassportHostTopologyTest(unittest.TestCase):
  """Unit tests to test the passport for switch related methods."""

  def setUp(self):
    super().setUp()
    patchers = [
        mock.patch(
            'lib.pasit.passport.passport_host.PassportHost._connect_to_service',
        ),
        mock.patch(
            'lib.pasit.passport.passport_host.PassportHost._validate_topology_switches',
        ),
        mock.patch(
            'lib.pasit.passport.passport_host.PassportHost._activate_usb_testers',
        ),
        mock.patch(
            'lib.pasit.passport.passport_host.PassportHost._setup_ip_power_clients',
        ),
    ]
    for patcher in patchers:
      patcher.start()
      self.addCleanup(patcher.stop)

  def test_get_paths_by_type(self):
    """Tests that we can get all the paths for a given device type and tag."""
    EXPECTED_PATHS = {
        'simple': {
            'DOCK': [],
            'DAISY_CHAIN': [],
            'DOCKLESS': [],
            None: [['dut-12345', 'switch1', 'monitor1']],
        },
        'pasit-full': {
            'DOCK': [],
            'DAISY_CHAIN': [],
            'DOCKLESS': [],
            None: [
                ['dut-34567', '1912901', 'dock_1', '2007901', 'monitor_1'],
                ['dut-34567', '1912901', 'dock_1', '2109002', 'monitor_2'],
            ],
        },
        'pasit-box': {
            'DOCK': [
                ['dut-23456', '2209501', 'dock_1', '2007901', 'monitor_1'],
                ['dut-23456', '2209501', 'dock_1', '2007902', 'monitor_2'],
            ],
            'DAISY_CHAIN': [
                ['dut-23456', '2209501', 'monitor_1'],
                ['dut-23456', '2209501', 'monitor_1', '2109002', 'monitor_2'],
            ],
            'DOCKLESS': [['dut-23456', '2209501', 'monitor_1']],
            None: [
                ['dut-23456', '2209501', 'dock_1', '2007901', 'monitor_1'],
                # Note this isn't a valid path for testing but it is a valid
                # path simply based on traversing the topology.
                [
                    'dut-23456',
                    '2209501',
                    'dock_1',
                    '2007901',
                    'monitor_1',
                    '2109002',
                    'monitor_2',
                ],
                ['dut-23456', '2209501', 'dock_1', '2007902', 'monitor_2'],
                ['dut-23456', '2209501', 'monitor_1'],
                ['dut-23456', '2209501', 'monitor_1', '2109002', 'monitor_2'],
            ],
        },
    }
    for topology_name, topology in TEST_TOPOLOGY.items():
      host = passport_host.PassportHost(config={'host_topology': topology})
      for tag in ['DOCK', 'DOCKLESS', 'DAISY_CHAIN', None]:
        with self.subTest(topology_name=topology_name, tag=tag):
          paths = host.get_paths_by_type(
              pasit_host_pb2.PasitHost.Device.Type.MONITOR, tag
          )
          expected_paths = EXPECTED_PATHS[topology_name][tag]
          if tag is None and topology_name == 'pasit-full':
            print(f'paths: {paths}')
            print(f'expected_paths: {expected_paths}')
          self.assertEqual(
              paths,
              expected_paths,
              f'Paths are not correct for name: {topology_name}, tag: {tag}.',
          )


if __name__ == '__main__':
  unittest.main()
