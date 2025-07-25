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

import unittest
from unittest import mock

from chromiumos.test.lab.api import pasit_host_pb2
from chromiumos.test.lab.api.passport import switch_service_pb2
from lib.pasit.passport import errors
from lib.pasit.passport import passport_host

_TEST_TOPOLOGY = {
    'hostname': 'localhost:1234',
    'devices': [
        {'id': 'dut', 'type': 'DUT'},
        {'id': 'switch1', 'type': 'SWITCH_FIXTURE'},
        {'id': 'switch2', 'type': 'SWITCH_FIXTURE'},
        {'id': 'switch3', 'type': 'SWITCH_FIXTURE'},
        {'id': 'switch4', 'type': 'SWITCH_FIXTURE'},
        {'id': 'camera1', 'type': 'CAMERA'},
        {'id': 'dock', 'type': 'DOCKING_STATION'},
        {'id': 'monitor1', 'type': 'MONITOR'},
    ],
    'connections': [
        {
            'parent_id': 'dut',
            'child_id': 'switch1',
            'tags': ['tag1'],
        },
        {
            'parent_id': 'switch1',
            'child_id': 'dock',
            'parent_port': 'A',
            'tags': ['tag1'],
        },
        {
            'parent_id': 'dock',
            'child_id': 'switch2',
            'tags': ['tag1'],
        },
        {
            'parent_id': 'switch2',
            'child_id': 'monitor1',
            'tags': ['tag1', 'tag2'],
        },
        {'parent_id': 'dut', 'child_id': 'switch3'},
        {'parent_id': 'switch3', 'child_id': 'camera1'},
        {'parent_id': 'dut', 'child_id': 'switch4', 'tags': ['tag3']},
        {'parent_id': 'switch4', 'child_id': 'monitor1', 'tags': ['tag3']},
    ],
}


class PassportHostSwitchesTest(unittest.TestCase):
  """Unit tests to test the passport for switch related methods."""

  def setUp(self):
    super().setUp()
    self.mock_switch_client = mock.Mock()

    get_switches_response = switch_service_pb2.GetSwitchesResponse(
        switches=[
            switch_service_pb2.SwitchFixture(id='switch1'),
            switch_service_pb2.SwitchFixture(id='switch2'),
            switch_service_pb2.SwitchFixture(id='switch3'),
            switch_service_pb2.SwitchFixture(id='switch4'),
        ]
    )
    self.mock_switch_client.get_switches.return_value = get_switches_response

    patchers = [
        mock.patch(
            'lib.pasit.passport.passport_switch_service_client.PassportSwitchServiceClient',
            return_value=self.mock_switch_client,
        ),
    ]
    for patcher in patchers:
      patcher.start()
      self.addCleanup(patcher.stop)

    config = {'host_topology': _TEST_TOPOLOGY}
    self.host = passport_host.PassportHost(config)

  def test_activate_device_by_id(self):
    self.host.activate_device_by_id('camera1')
    self.mock_switch_client.enable_switch.assert_called_once_with('switch3', '')

  def test_deactivate_device_by_id(self):
    self.host.deactivate_device_by_id('camera1')
    self.mock_switch_client.disable_switch.assert_called_once_with(
        'switch3', ''
    )

  def test_activate_device_by_id_with_tag(self):
    self.host.activate_device_by_id('monitor1', tag='tag1')
    self.mock_switch_client.enable_switch.assert_has_calls(
        [mock.call('switch1', 'A'), mock.call('switch2', '')], any_order=True
    )
    self.assertEqual(self.mock_switch_client.enable_switch.call_count, 2)

  def test_activate_device_by_id_with_wrong_tag_raises_error(self):
    with self.assertRaises(errors.DevicePathNotFoundError):
      self.host.activate_device_by_id('monitor1', tag='nonexistent_tag')

  def test_activate_device_by_type(self):
    self.host.activate_device_by_type(
        pasit_host_pb2.PasitHost.Device.Type.CAMERA
    )
    self.mock_switch_client.enable_switch.assert_called_once_with('switch3', '')

  def test_deactivate_device_by_type(self):
    self.host.deactivate_device_by_type(
        pasit_host_pb2.PasitHost.Device.Type.CAMERA
    )
    self.mock_switch_client.disable_switch.assert_called_once_with(
        'switch3', ''
    )

  def test_activate_device_by_type_with_tag(self):
    self.host.activate_device_by_type(
        pasit_host_pb2.PasitHost.Device.Type.MONITOR, tag='tag1'
    )
    self.mock_switch_client.enable_switch.assert_has_calls(
        [mock.call('switch1', 'A'), mock.call('switch2', '')], any_order=True
    )
    self.assertEqual(self.mock_switch_client.enable_switch.call_count, 2)
    self.mock_switch_client.reset_mock()
    self.host.activate_device_by_type(
        pasit_host_pb2.PasitHost.Device.Type.MONITOR, tag='tag3'
    )
    self.mock_switch_client.enable_switch.assert_called_once_with('switch4', '')

  def test_deactivate_device_by_type_with_tag(self):
    self.host.deactivate_device_by_type(
        pasit_host_pb2.PasitHost.Device.Type.MONITOR, tag='tag1'
    )
    self.mock_switch_client.disable_switch.assert_has_calls(
        [mock.call('switch1', 'A'), mock.call('switch2', '')], any_order=True
    )
    self.assertEqual(self.mock_switch_client.disable_switch.call_count, 2)


if __name__ == '__main__':
  unittest.main()
