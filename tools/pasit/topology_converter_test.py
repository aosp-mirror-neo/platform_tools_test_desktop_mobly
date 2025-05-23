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

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from google.protobuf import json_format

import topology_converter

TEST_DATA = [
    {
        'name': 'simple',
        'json': """{
	"devices":  [
		{
			"id":  "dut_hostname",
			"type":  "DUT"
		},
		{
			"id":  "child_1",
			"type":  "SWITCH_FIXTURE"
		},
		{
			"id":  "child_2",
			"type":  "MONITOR"
		}
	],
	"connections":  [
		{
			"parentId":  "dut_hostname",
			"childId":  "child_1",
			"type":  "CHILD_TYPE_1"
		},
		{
			"parentId":  "child_1",
			"childId":  "child_2",
			"type":  "CHILD_TYPE_2"
		}
	]
}
""",
        'yaml': """TestBeds:
- Name: pasit-android-testbed
  TestParams:
    servo_host: localhost
    servo_port: 9999
  Controllers:
    AndroidDevice: '*'
    PassportHost:
    - service_host: localhost
      service_port: 8300
      host_topology:
        devices:
        - id: dut_hostname
          type: DUT
        - id: child_1
          type: SWITCH_FIXTURE
        - id: child_2
          type: MONITOR
        connections:
        - parentId: dut_hostname
          childId: child_1
          type: CHILD_TYPE_1
        - parentId: child_1
          childId: child_2
          type: CHILD_TYPE_2
""",
        'dot': b"""digraph Topology {
    "dut_hostname" [label="dut_hostname\nDUT"];
    "child_1" [label="child_1\nSWITCH_FIXTURE"];
    "child_2" [label="child_2\nMONITOR"];
    "dut_hostname" -> "child_1" [label="CHILD_TYPE_1"];
    "child_1" -> "child_2" [label="CHILD_TYPE_2"];
}""",
    },
    {
        'name': 'multiple_paths',
        'json': """{
	"devices":  [
		{
			"id":  "dut_hostname",
			"type":  "DUT"
		},
		{
			"id":  "child_1",
			"type":  "SWITCH_FIXTURE"
		},
		{
			"id":  "child_2",
			"type":  "MONITOR"
		},
    {
			"id":  "child_3",
			"type":  "SWITCH_FIXTURE"
		}
	],
	"connections":  [
		{
			"parentId":  "dut_hostname",
			"childId":  "child_1",
			"type":  "CHILD_TYPE_1"
		},
		{
			"parentId":  "child_1",
			"childId":  "child_2",
			"type":  "CHILD_TYPE_2"
		},
    {
			"parentId":  "child_3",
			"childId":  "child_2",
			"type":  "CHILD_TYPE_2_ALTERNATE_PATH"
		},
    {
			"parentId":  "dut_hostname",
			"childId":  "child_3",
			"type":  "CHILD_TYPE_3"
		}
	]
}
""",
        'yaml': """TestBeds:
- Name: pasit-android-testbed
  TestParams:
    servo_host: localhost
    servo_port: 9999
  Controllers:
    AndroidDevice: '*'
    PassportHost:
    - service_host: localhost
      service_port: 8300
      host_topology:
        devices:
        - id: dut_hostname
          type: DUT
        - id: child_1
          type: SWITCH_FIXTURE
        - id: child_2
          type: MONITOR
        - id: child_3
          type: SWITCH_FIXTURE
        connections:
        - parentId: dut_hostname
          childId: child_1
          type: CHILD_TYPE_1
        - parentId: child_1
          childId: child_2
          type: CHILD_TYPE_2
        - parentId: child_3
          childId: child_2
          type: CHILD_TYPE_2_ALTERNATE_PATH
        - parentId: dut_hostname
          childId: child_3
          type: CHILD_TYPE_3
""",
        'dot': b"""digraph Topology {
    "dut_hostname" [label="dut_hostname\nDUT"];
    "child_1" [label="child_1\nSWITCH_FIXTURE"];
    "child_2" [label="child_2\nMONITOR"];
    "child_3" [label="child_3\nSWITCH_FIXTURE"];
    "dut_hostname" -> "child_1" [label="CHILD_TYPE_1"];
    "child_1" -> "child_2" [label="CHILD_TYPE_2"];
    "child_3" -> "child_2" [label="CHILD_TYPE_2_ALTERNATE_PATH"];
    "dut_hostname" -> "child_3" [label="CHILD_TYPE_3"];
}""",
    },
    {
        'name': 'circular_topology',
        'json': """{
	"devices":  [
		{
			"id":  "dut_hostname",
			"type":  "DUT"
		},
		{
			"id":  "child_1",
			"type":  "SWITCH_FIXTURE"
		},
		{
			"id":  "child_2",
			"type":  "MONITOR"
		}
	],
	"connections":  [
		{
			"parentId":  "dut_hostname",
			"childId":  "child_1",
			"type":  "CHILD_TYPE_1"
		},
		{
			"parentId":  "child_1",
			"childId":  "child_2",
			"type":  "CHILD_TYPE_2"
		},
    {
			"parentId":  "child_2",
			"childId":  "dut_hostname",
			"type":  "CHILD_TYPE_CIRCULAR_PATH"
		}
	]
}
""",
        'yaml': """TestBeds:
- Name: pasit-android-testbed
  TestParams:
    servo_host: localhost
    servo_port: 9999
  Controllers:
    AndroidDevice: '*'
    PassportHost:
    - service_host: localhost
      service_port: 8300
      host_topology:
        devices:
        - id: dut_hostname
          type: DUT
        - id: child_1
          type: SWITCH_FIXTURE
        - id: child_2
          type: MONITOR
        connections:
        - parentId: dut_hostname
          childId: child_1
          type: CHILD_TYPE_1
        - parentId: child_1
          childId: child_2
          type: CHILD_TYPE_2
        - parentId: child_2
          childId: dut_hostname
          type: CHILD_TYPE_CIRCULAR_PATH
""",
        'dot': b"""digraph Topology {
    "dut_hostname" [label="dut_hostname\nDUT"];
    "child_1" [label="child_1\nSWITCH_FIXTURE"];
    "child_2" [label="child_2\nMONITOR"];
    "dut_hostname" -> "child_1" [label="CHILD_TYPE_1"];
    "child_1" -> "child_2" [label="CHILD_TYPE_2"];
    "child_2" -> "dut_hostname" [label="CHILD_TYPE_CIRCULAR_PATH"];
}""",
    },
]


class TopologyConverterTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self.temp_dir = tempfile.mkdtemp(prefix='shared_test_')
    self.test_json_file = os.path.join(self.temp_dir, 'test_topology.json')
    self.test_yaml_file = os.path.join(self.temp_dir, 'test_topology.yaml')
    self.test_graph_file = os.path.join(self.temp_dir, 'test_topology.png')

  def tearDown(self):
    super().tearDown()
    # Remove test files
    shutil.rmtree(self.temp_dir)

  def test_convert_json_to_yaml(self):
    for _, case in enumerate(TEST_DATA):
      json_data = case['json']
      yaml_data = case['yaml']
      with self.subTest(name=f'test_case_{case["name"]}'):
        # Create test JSON file
        with open(self.test_json_file, 'w') as f:
          f.write(json_data)
        outfile = os.path.join(self.temp_dir, 'test_topology_output.yaml')
        topology = topology_converter.parse_json(self.test_json_file)
        topology_converter.write_to_mobly_yaml(topology, outfile)
        self.assertTrue(os.path.exists(outfile))
        with open(outfile, 'r') as f:
          data = f.read()
        self.assertEqual(data, yaml_data)
        os.remove(outfile)

  def test_convert_yaml_to_json(self):
    for _, case in enumerate(TEST_DATA):
      json_data = case['json']
      yaml_data = case['yaml']
      with self.subTest(name=f'test_case_{case["name"]}'):
        # Create test files
        with open(self.test_yaml_file, 'w') as f:
          f.write(yaml_data)
        with open(self.test_json_file, 'w') as f:
          f.write(json_data)
        # test conversion from yaml to json
        outfile = os.path.join(self.temp_dir, 'test_topology_output.json')
        topology = topology_converter.parse_yaml(self.test_yaml_file)
        with open(outfile, 'w') as f:
          f.write(json_format.MessageToJson(topology))
        self.assertTrue(os.path.exists(outfile))
        with open(outfile, 'r') as f:
          data = json.load(f)
        with open(self.test_json_file, 'r') as f:
          expected_data = json.load(f)
        self.assertEqual(data, expected_data)
        os.remove(outfile)

  def test_generate_graph_json(self):
    for _, case in enumerate(TEST_DATA):
      json_data = case['json']
      dot_data = case['dot']
      with self.subTest(name=f'test_case_{case["name"]}'):
        with open(self.test_json_file, 'w') as f:
          f.write(json_data)
        with mock.patch('subprocess.Popen') as mock_popen:
          mock_process = setup_mock_popen(mock_popen)
          topology_converter.generate_graph(
              self.test_json_file, self.test_graph_file
          )
          validate_mock_popen(
              mock_popen, mock_process, self.test_graph_file, dot_data
          )

  def test_generate_graph_yaml(self):
    for _, case in enumerate(TEST_DATA):
      yaml_data = case['yaml']
      dot_data = case['dot']
      with self.subTest(name=f'test_case_{case["name"]}'):
        with open(self.test_yaml_file, 'w') as f:
          f.write(yaml_data)
        with mock.patch('subprocess.Popen') as mock_popen:
          mock_process = setup_mock_popen(mock_popen)
          topology_converter.generate_graph(
              self.test_yaml_file, self.test_graph_file
          )
          validate_mock_popen(
              mock_popen, mock_process, self.test_graph_file, dot_data
          )


def setup_mock_popen(mock_popen):
  mock_process = mock.MagicMock()
  mock_process.communicate.return_value = (b'', b'')
  mock_process.returncode = 0
  mock_popen.return_value = mock_process
  return mock_process


def validate_mock_popen(
    mock_popen, mock_process, expected_file_name, expected_data
):
  mock_popen.assert_called_once_with(
      ['dot', '-Tpng', '-o', expected_file_name],
      stdin=subprocess.PIPE,
      stderr=subprocess.PIPE,
  )
  mock_process.communicate.assert_called_once_with(expected_data)


if __name__ == '__main__':
  unittest.main()
