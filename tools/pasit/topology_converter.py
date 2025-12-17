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

JSON format is compatible with shivas format and can be used to set topology
in the lab.  YAML format is compatible with Mobly testbed configs and
can be used to develop and run mobly tests.  Textproto format is compatible
with legacy Tast tests and should not be used for shivas.

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
import json
import os
import subprocess
import sys
import urllib.parse

from chromiumos.test.lab.api import pasit_host_pb2
from chromiumos.test.lab.api import rpm_pb2
from google.protobuf import json_format
from google.protobuf import text_format
import yaml


def parse_json(
    json_file: str, ignore_unknown_fields: bool = False
) -> pasit_host_pb2.PasitHost:
  """Parses the pasit topology from a JSON file.

  Args:
    json_file: string path to a JSON file containing a pasit topology.
    ignore_unknown_fields: If True, unknown fields in the JSON will be ignored.

  Returns:
    A pasit_host_pb2.PasitHost object.

  Raises:
    FileNotFoundError: if the JSON file is not found.
    json_format.ParseError: if the JSON file is invalid.
  """
  pasit_host = pasit_host_pb2.PasitHost()
  with open(json_file, 'r') as f:
    data = f.read()
    data = _convert_ufs_rpm_to_proto_json(data)
    json_format.Parse(
        data, pasit_host, ignore_unknown_fields=ignore_unknown_fields
    )
  return pasit_host


def _convert_ufs_rpm_to_proto_json(json_data: str) -> str:
  """Converts the RPM data from JSON to proto format.

  The UFS data uses a different format than the pasit_host.proto.  This method
  converts the data to the format used in pasit_host.proto, so that it can be
  ingested as a pasit_host.proto.
  """
  json_data = json.loads(json_data)
  for device in json_data['devices']:
    ufs_rpm = device.get('rpm')
    if ufs_rpm is None:
      continue
    hostname = ufs_rpm.get('powerunitName')
    if hostname is None:
      raise ValueError('powerunitName is required for RPMs.')
    outlet = ufs_rpm.get('powerunitOutlet')
    if outlet is None:
      raise ValueError('powerunitOutlet is required for RPMs.')
    powerunit_type = ufs_rpm.get('powerunitType')
    if powerunit_type is not None and powerunit_type != 'TYPE_IP9850':
      raise ValueError(f'Only IP9850 RPMs are supported {powerunit_type}.')
    parsed_hostname = urllib.parse.urlsplit(f'//{hostname}')
    device['rpm'] = {
        'present': True,
        'powerUnitHostname': {'address': parsed_hostname.hostname},
        'powerUnitOutlet': outlet,
        'type': rpm_pb2.RPMType.RPM_TYPE_IP9850,
    }
    if parsed_hostname.port:
      device['rpm']['powerUnitHostname']['port'] = parsed_hostname.port
  return json.dumps(json_data)


def _convert_output_to_ufs_format(json_data: str) -> str:
  """Converts the output data from proto format to UFS format."""
  json_data = json.loads(json_data)
  for device in json_data['devices']:
    rpm_proto = device.get('rpm')
    if rpm_proto is None:
      continue
    hostname = rpm_proto.get('powerUnitHostname').get('address')
    if hostname is None:
      raise ValueError('powerUnitHostname is required for RPMs.')
    port = rpm_proto.get('powerUnitHostname').get('port')
    combined_hostname = f'{hostname}:{port}' if port else hostname
    outlet = rpm_proto.get('powerUnitOutlet')
    if outlet is None:
      raise ValueError('powerUnitOutlet is required for RPMs.')
    powerunit_type = rpm_proto.get('type')
    if powerunit_type != 'RPM_TYPE_IP9850':
      raise ValueError(f'Only IP9850 RPMs are supported {powerunit_type}.')
    device['rpm'] = {
        'powerunitName': combined_hostname,
        'powerunitOutlet': outlet,
        'powerunitType': 'TYPE_IP9850',
    }
  return json.dumps(json_data, indent=2)


def write_to_mobly_yaml(topology: pasit_host_pb2.PasitHost, yaml_file: str):
  """Converts a PASIT topoloygy to a mobly compatible YAML file.

  Args:
    topology: a pasit_host_pb2.PasitHost object that will be converted to YAML.
    yaml_file: string path to a YAML file to write the converted topology.
  """
  topology_dict = json_format.MessageToDict(topology)
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


def write_to_json(topology: pasit_host_pb2.PasitHost, output_file: str):
  json_data = json_format.MessageToJson(topology)
  json_data = _convert_output_to_ufs_format(json_data)
  with open(output_file, 'w') as f:
    f.write(json_data)


def parse_yaml(
    yaml_file: str, ignore_unknown_fields: bool = False
) -> pasit_host_pb2.PasitHost:
  """Parses the pasit topology from a YAML file.

  Args:
    yaml_file: string path to a YAML file containing a Mobly testbed config.
    ignore_unknown_fields: If True, unknown fields in the JSON representation
      within the YAML will be ignored.

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
  json_format.ParseDict(
      topologies[topology_name],
      pasit_host,
      ignore_unknown_fields=ignore_unknown_fields,
  )
  return pasit_host


def parse_textproto(
    textproto_file: str, ignore_unknown_fields: bool = False
) -> pasit_host_pb2.PasitHost:
  """Parses the pasit topology from a textproto file."""
  pasit_host = pasit_host_pb2.PasitHost()
  with open(textproto_file, 'r') as f:
    data = f.read()
    text_format.Parse(
        data, pasit_host, allow_unknown_field=ignore_unknown_fields
    )
  return pasit_host


def generate_graph(
    input_file: str, output_file: str, ignore_unknown_fields: bool = False,
    dot_binary: bool = 'dot'
):
  """Generates a graph image from a topology file.

  Args:
    input_file: string path to a JSON or YAML file containing a pasit topology.
    output_file: string path to a PNG file to write the graph image.
    ignore_unknown_fields: bool indicating if unknown fields should be skipped.
    dot_binary: path to 'dot' executable if not available in PATH.
  """
  # extract the file type from extension
  file_type = os.path.splitext(input_file)[1]
  if file_type == '.json':
    topology = parse_json(
        input_file, ignore_unknown_fields=ignore_unknown_fields
    )
  elif file_type == '.yaml' or file_type == '.yml':
    topology = parse_yaml(
        input_file, ignore_unknown_fields=ignore_unknown_fields
    )
  elif file_type == '.textproto':
    topology = parse_textproto(
        input_file, ignore_unknown_fields=ignore_unknown_fields
    )
  else:
    print(f'Unsupported file type: {file_type}')
    return

  graph_content = '''digraph Topology {
    node [shape=plain];
    ranksep = 1.2;
  '''
  for device in topology.devices:
    ports = ''
    for connection in topology.connections:
      if device.id == connection.parent_id:
        if connection.parent_port:
          conn_type = "" if connection.parent_port == '' else connection.parent_port
          ports += f'<TR><TD PORT="p{connection.parent_port}"> Port {conn_type} </TD></TR>\n'

    graph_content += (
        f'"{device.id}"'
        f''' [label=<
              <TABLE BORDER="2" CELLBORDER="1" CELLSPACING="0">
                  <TR><TD>{device.id}<BR/>{pasit_host_pb2.PasitHost.Device.Type.Name(device.type)}</TD></TR>
                  {ports}
              </TABLE>>];\n
          '''
  )
  for connection in topology.connections:
    parent_port = f':"p{connection.parent_port}"' if connection.parent_port != '' else ''
    label = f'label="Tags: [{','.join(str(x) for x in connection.tags)}]"'
    label = label if label != 'label="Tags: []"' else ''
    graph_content += (
        f'''"{connection.parent_id}"{parent_port} -> "{connection.child_id}" [
            labeldistance="10",
            {label}
          ];\n
        '''
    )

  graph_content += "}"

  # Use graphviz to generate the graph image to PNG
  dot_process = subprocess.Popen(
      [dot_binary, '-Tpng', '-o', output_file],
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
  convert_parser.add_argument(
      '--ignore-unknown-fields',
      action='store_true',
      help='Ignore unknown fields during protobuf parsing.',
  )

  # Graph command
  graph_parser = subparsers.add_parser('graph', help='Generate a graph image')
  graph_parser.add_argument(
      '-i', '--input-file', help='Input file (JSON or YAML)'
  )
  graph_parser.add_argument(
      '-o', '--output-file', help='Output image file (e.g., topology.png)'
  )
  graph_parser.add_argument(
      '--ignore-unknown-fields',
      action='store_true',
      help='Ignore unknown fields during protobuf parsing.',
  )

  args = parser.parse_args()
  if args.command == 'convert':
    input_file = args.input_file
    output_file = args.output_file
    if not input_file or not output_file:
      parser.print_help()
      print('Input and output files are required for conversion.')
      sys.exit(1)
    topology = None
    if input_file.endswith('.json'):
      topology = parse_json(
          input_file, ignore_unknown_fields=args.ignore_unknown_fields
      )
    elif input_file.endswith('.yaml') or input_file.endswith('.yml'):
      topology = parse_yaml(
          input_file, ignore_unknown_fields=args.ignore_unknown_fields
      )
    elif input_file.endswith('.textproto'):
      topology = parse_textproto(
          input_file, ignore_unknown_fields=args.ignore_unknown_fields
      )
    else:
      print(
          'Invalid input file type for conversion.  Input must be json, yaml,'
          ' or textproto.'
      )
    if not topology:
      print('Failed to parse input file.')
      sys.exit(1)
    if output_file.endswith('.json'):
      write_to_json(topology, output_file)
    elif output_file.endswith('.yaml') or output_file.endswith('.yml'):
      write_to_mobly_yaml(topology, output_file)
    elif output_file.endswith('.textproto'):
      with open(output_file, 'w') as f:
        f.write(text_format.MessageToString(topology))
    else:
      print(
          'Invalid output file type for conversion.  Output must be json,'
          ' yaml, or textproto.'
      )
  elif args.command == 'graph':
    if not args.input_file or not args.output_file:
      parser.print_help()
      print('Input and output files are required for graph generation.')
      sys.exit(1)
    generate_graph(
        args.input_file,
        args.output_file,
        ignore_unknown_fields=args.ignore_unknown_fields,
    )
  else:
    parser.print_help()
    sys.exit(1)


if __name__ == '__main__':
  main()
