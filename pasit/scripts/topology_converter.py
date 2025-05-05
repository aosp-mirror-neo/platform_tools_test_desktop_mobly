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

r"""Converts PASIT topology between JSON and YAML.

JSON format is compatible with pasit_host.proto format and can be used to set
topology in the lab.  YAML format is compatible with Mobly testbed configs and
can be used to develop and run mobly tests.

To Convert between JSON to YAML:

topology_converter convert -i \
  /full/path/to/topology.json -o /ful/path/to/topology.yaml

topology_converter convert -i \
  /full/path/to/topology.yaml -o /full/path/to/topology.json

To generate a image visualization of the topology:
topology_converter graph -i \
  /full/path/to/topology.yaml -o /full/path/to/topology.png
"""

import argparse
import os
import subprocess
import sys
from google.protobuf import json_format
import yaml
from chromiumos.test.lab.api import pasit_host_pb2


def parse_json(json_file: str) -> pasit_host_pb2.PasitHost:
  """Parses the pasit topology from a JSON file.

  Args:
    json_file: string path to a JSON file containing a pasit topology.

  Returns:
    A pasit_host_pb2.PasitHost object.
  Raises:
    FileNotFoundError: if the JSON file is not found.
    json_format.ParseError: if the JSON file is invalid.
  """
  pasit_host = pasit_host_pb2.PasitHost()
  with open(json_file, 'r') as f:
    data = f.read()
    json_format.Parse(data, pasit_host)
  return pasit_host


def convert_json_to_yaml(json_file: str, yaml_file: str):
  """Converts a JSON file to a YAML file.

  Args:
    json_file: string path to a JSON file containing a pasit topology.
    yaml_file: string path to a YAML file to write the converted topology.
  """
  data = parse_json(json_file)
  topology_dict = json_format.MessageToDict(data)
  topology = {
      'TestBeds': [{
          'Name': 'pasit-android-testbed',
          'TestParams': {
              'servo_host': 'localhost',
              'servo_port': 9999,
          },
          'Controllers': {
              'AndroidDevice': '*',
              'PassportHost': [{
                  'service_host': 'localhost',
                  'service_port': 8300,
                  'host_topology': topology_dict,
              }],
          },
      }]
  }

  with open(yaml_file, 'w') as f:
    yaml.dump(topology, f, indent=2, sort_keys=False)


def parse_yaml(yaml_file: str) -> pasit_host_pb2.PasitHost:
  """Parses the pasit topology from a YAML file.

  Args:
    yaml_file: string path to a YAML file containing a Mobly testbed config.

  Returns:
    A pasit_host_pb2.PasitHost object.
  Raises:
    FileNotFoundError: if the YAML file is not found.
    ValueError: if the YAML file is invalid or does not contain a topology in
    the expected format.
  """
  try:
    with open(yaml_file, 'r') as f:
      data = yaml.safe_load(f)
  except yaml.YAMLError as e:
    raise ValueError(f'Error: YAML file is invalid: {yaml_file}') from e

  if not data:
    raise ValueError(f'Error: YAML file is empty: {yaml_file}')

  testbeds = data.get('TestBeds')
  if not testbeds:
    raise ValueError(
        f'Error: YAML file does not contain "TestBeds" key: {yaml_file}'
    )

  topologies = {}
  for testbed in testbeds:
    if 'Name' not in testbed:
      raise ValueError(
          f'Error: YAML file does not contain "Name" key: {yaml_file}'
      )
    name = testbed['Name']
    if 'Controllers' not in testbed:
      print(f'Skipping testbed {name} as it does not have "Controllers" key')
      continue
    if 'PassportHost' not in testbed['Controllers']:
      print(f'Skipping testbed {name} as it does not have "PasportHost" key')
      continue
    for controller in testbed['Controllers']['PassportHost']:
      if 'host_topology' in controller:
        topology = controller['host_topology']
        topologies[testbed['Name']] = topology

  if not topologies:
    raise ValueError(
        f'Error: YAML file does not contain any topologies: {yaml_file}'
    )
  topology_name = list(topologies.keys())[0]
  if len(topologies) > 1:
    print(
        f'Warning: YAML file contains multiple topologies: {yaml_file} using'
        f' the first one {topology_name}.'
    )

  pasit_host = pasit_host_pb2.PasitHost()
  json_format.ParseDict(topologies[topology_name], pasit_host)
  return pasit_host


def convert_yaml_to_json(yaml_file: str, json_file: str):
  """Converts a YAML file to a JSON file.

  Args:
    yaml_file: string path to a YAML file containing a Mobly testbed config.
    json_file: string path to a JSON file to write the converted topology.
  """
  topology = parse_yaml(yaml_file)
  with open(json_file, 'w') as f:
    f.write(json_format.MessageToJson(topology, indent=2))


def generate_graph(input_file: str, output_file: str):
  """Generates a graph image from a topology file.

  Args:
    input_file: string path to a JSON or YAML file containing a pasit topology.
    output_file: string path to a PNG file to write the graph image.
  """
  # extract the file type from extension
  file_type = os.path.splitext(input_file)[1]
  if file_type == '.json':
    topology = parse_json(input_file)
  elif file_type == '.yaml' or file_type == '.yml':
    topology = parse_yaml(input_file)
  else:
    print(f'Unsupported file type: {file_type}')
    return

  graph_content = 'digraph Topology {\n'
  for device in topology.devices:
    graph_content += (
        f'    "{device.id}"'
        f' [label="{device.id}\n{pasit_host_pb2.PasitHost.Device.Type.Name(device.type)}"];\n'
    )
  for connection in topology.connections:
    graph_content += (
        f'    "{connection.parent_id}" -> "{connection  .child_id}"'
        f' [label="{connection.type}"];\n'
    )
  graph_content += '}'

  # Use graphviz to generate the graph image to PNG
  dot_process = subprocess.Popen(
      ['dot', '-Tpng', '-o', output_file],
      stdin=subprocess.PIPE,
      stderr=subprocess.PIPE,
  )
  dot_process.communicate(graph_content.encode())


def main():
  parser = argparse.ArgumentParser(
      description=(
          'Convert PASIT topology between JSON and YAML, and generate a graph'
          ' of the topology.'
      )
  )
  subparsers = parser.add_subparsers(dest='command', help='Available commands')

  # Convert command
  convert_parser = subparsers.add_parser(
      'convert', help='Convert between JSON and YAML'
  )
  convert_parser.add_argument(
      '-i', '--input-file', help='Input file (JSON or YAML)'
  )
  convert_parser.add_argument(
      '-o', '--output-file', help='Output file (JSON or YAML)'
  )

  # Graph command
  graph_parser = subparsers.add_parser('graph', help='Generate a graph image')
  graph_parser.add_argument(
      '-i', '--input-file', help='Input file (JSON or YAML)'
  )
  graph_parser.add_argument(
      '-o', '--output-file', help='Output image file (e.g., topology.png)'
  )

  args = parser.parse_args()

  if args.command == 'convert':
    input_file = args.input_file
    output_file = args.output_file
    if not input_file or not output_file:
      parser.print_help()
      print('Input and output files are required for conversion.')
      sys.exit(1)
    if input_file.endswith('.json') and output_file.endswith('.yaml'):
      convert_json_to_yaml(input_file, output_file)
    elif input_file.endswith('.yaml') and output_file.endswith('.json'):
      convert_yaml_to_json(input_file, output_file)
    else:
      print(
          'Invalid file type combination for conversion.  Input must be json or'
          ' yaml and the opposite for output.'
      )
  elif args.command == 'graph':
    if not args.input_file or not args.output_file:
      parser.print_help()
      print('Input and output files are required for graph generation.')
      sys.exit(1)
    generate_graph(args.input_file, args.output_file)
  else:
    parser.print_help()
    sys.exit(1)


if __name__ == '__main__':
  main()
