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

"""Helper functions for modetest."""

import re
import subprocess
from typing import Any

from lib.pasit import pasit_device


def get_crtcs_count(dut: pasit_device.PasitDevice) -> int:
  """Gets the number of CRTCs from the device using 'modetest -p'.

  Args:
    dut: The DUT that accesses the shell.

  Returns:
    The number of CRTCs reported by the device.
  """
  try:
    output = dut.shell(["modetest", "-p"]).decode("utf-8", errors="ignore")
    lines = output.splitlines()

    crtc_count = 0
    in_crtc_section = False
    for line in lines:
      line_stripped = line.strip()
      if line_stripped == "CRTCs:":
        in_crtc_section = True
        continue
      if in_crtc_section:
        # Stop parsing if we've reached the "Planes:" section.
        if line_stripped == "Planes:":
          break
        # Skip the header line "id\tfb\tpos\tsize" and any blank lines.
        if line_stripped.startswith("id\t") or not line_stripped:
          continue
        # A CRTC entry line typically starts with its ID (a number).
        parts = line_stripped.split("\t")
        # Line looks like `82	305	(0,0)	(2256x1504)`
        if parts and len(parts) == 4 and parts[0].isdigit():
          crtc_count += 1
    return crtc_count
  except subprocess.CalledProcessError:
    return -1


def get_all_encoders_props(
    dut: pasit_device.PasitDevice,
) -> tuple[str, dict[int, dict[str, Any]]]:
  """Gets all encoders and their properties from 'modetest -e'.

  Args:
    dut: The DUT that accesses the shell.

  Returns:
    A tuple containing the raw modetest output and a dictionary mapping
    encoder IDs to their properties. Each property dictionary includes the
    encoder's 'crtc'. Returns an empty string and dict if the command fails.
    Example encoder dictionary:
    {
      708: { 'crtc': 199 },
      718: { 'crtc': 0 },
    }
  """
  try:
    output = dut.shell(["modetest", "-e"]).decode("utf-8", errors="ignore")
    return output, _parse_modetest_encoders_output(output)
  except subprocess.CalledProcessError:
    return "", {}


def get_all_connectors_props(
    dut: pasit_device.PasitDevice,
) -> tuple[str, dict[int, dict[str, Any]]]:
  """Gets all connectors and their properties from 'modetest -c'.

  Args:
    dut: The DUT that accesses the shell.

  Returns:
    A tuple containing the raw modetest output and a dictionary mapping
    connector IDs to their properties. Each property dictionary includes a
    'name', a 'connected' boolean, and the 'active_encoder'. Returns an empty
    string and dict if the command fails.
    Example connector dictionary:
    {
      709: {
        'name': 'eDP-1',
        'connected': True,
        'active_encoder': 708,
        'props': {
          'EDID': '00ffff...',
          'DPMS': '0',
        }
      },
      719: {
        'name': 'HDMI-A-1',
        'connected': False,
        'active_encoder': 0,
        'props': { ... }
      }
    }
  """
  try:
    output = dut.shell(["modetest", "-c"]).decode("utf-8", errors="ignore")
    return output, _parse_modetest_output(output)
  except subprocess.CalledProcessError:
    return "", {}


def _parse_modetest_output(output: str) -> dict[int, dict[str, Any]]:
  """Parses the output of 'modetest -c' to extract connector properties."""
  lines = output.splitlines()
  connectors = {}
  current_connector_id = None
  in_props_section = False
  # A prop line looks like: `  3  PATH:`
  prop_line_regex = r"\s+\d+\s+(.*):$"

  in_connectors_section = False
  for line_index, line in enumerate(lines):
    line_stripped = line.strip()
    if not in_connectors_section:
      if line_stripped == "Connectors:":
        in_connectors_section = True
      continue

    parts = line.split()
    # A connector line looks like:
    # 709     708     connected       eDP-1        280x190         2       708
    if (
        parts
        and parts[0].isdigit()
        and len(parts) >= 4
        and parts[2] in ["connected", "disconnected", "unknown"]
    ):
      current_connector_id = int(parts[0])
      connectors[current_connector_id] = {
          "name": parts[3],
          "connected": parts[2] == "connected",
          "active_encoder": int(parts[1]),
          "props": {},
      }
      in_props_section = False
      continue

    if current_connector_id is None:
      continue

    if line_stripped == "props:":
      in_props_section = True
      continue

    if not in_props_section:
      continue

    match = re.match(prop_line_regex, line)
    if match:
      prop_name = match.group(1).strip()
      prop_value = ""
      for value_line_index in range(line_index + 1, len(lines)):
        value_line = lines[value_line_index]
        value_line_stripped = value_line.strip()
        if value_line_stripped.startswith("value:"):
          prop_value = value_line_stripped.split(":", 1)[1].strip()
          if not prop_value and value_line_index + 1 < len(lines):
            # check indentation to see if it's a multi-line value
            if len(lines[value_line_index + 1]) > len(value_line) - len(
                value_line.lstrip()
            ):
              prop_value = lines[value_line_index + 1].strip()
          break
        elif re.match(prop_line_regex, value_line):  # next prop
          break
        else:  # Stop if we see what looks like a new connector
          next_parts = value_line.split()
          if (
              next_parts
              and next_parts[0].isdigit()
              and len(next_parts) >= 3
              and next_parts[2] in ["connected", "disconnected", "unknown"]
          ):
            break
      connectors[current_connector_id]["props"][prop_name] = prop_value

  return connectors


def _parse_modetest_encoders_output(output: str) -> dict[int, dict[str, Any]]:
  """Parses the output of 'modetest -e' to extract encoder properties."""
  lines = output.splitlines()
  encoders = {}
  in_encoders_section = False
  encoder_regex = re.compile(r"^\s*(\d+)\s+(\d+)\s+([A-Z]+)\s+.*")

  for line in lines:
    line_stripped = line.strip()
    if not in_encoders_section:
      if line_stripped == "Encoders:":
        in_encoders_section = True
      continue

    if line_stripped.startswith("id") or not line_stripped:
      continue

    match = encoder_regex.match(line)
    if match:
      encoder_id = int(match.group(1))
      crtc_id = int(match.group(2))
      encoders[encoder_id] = {"crtc": crtc_id}

  return encoders
