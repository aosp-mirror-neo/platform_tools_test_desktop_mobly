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


def get_all_connectors_props(
    dut: pasit_device.PasitDevice,
) -> tuple[str, dict[int, dict[str, Any]]]:
  """Gets all connectors and their properties from 'modetest -c'.

  Args:
    dut: The DUT that accesses the shell.

  Returns:
    A tuple containing the raw modetest output and a dictionary mapping
    connector IDs to their properties. Each property dictionary includes a
    'name' and a 'connected' boolean. Returns an empty string and dict if the
    command fails.
    Example connector dictionary:
    {
      709: {
        'name': 'eDP-1',
        'connected': True,
        'props': {
          'EDID': '00ffff...',
          'DPMS': '0',
        }
      },
      719: {
        'name': 'HDMI-A-1',
        'connected': False,
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
  prop_line_regex = r"^\s+\d+\s+(.*):$"

  in_connectors_section = False
  i = 0
  while i < len(lines):
    line = lines[i]
    line_stripped = line.strip()

    if not in_connectors_section:
      if line_stripped == "Connectors:":
        in_connectors_section = True
      i += 1
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
          "props": {},
      }
      in_props_section = False
      i += 1
      continue

    if current_connector_id is None:
      i += 1
      continue

    if line_stripped == "props:":
      in_props_section = True
      i += 1
      continue

    if not in_props_section:
      i += 1
      continue

    match = re.match(prop_line_regex, line)
    if match:
      prop_name = match.group(1).strip()
      prop_value = ""

      # Find "value:" line for this prop
      value_line_index = -1
      for j in range(i + 1, len(lines)):
        # Stop if we hit the next property or connector
        if re.match(prop_line_regex, lines[j]):
          break
        next_parts = lines[j].split()
        if (
            next_parts
            and next_parts[0].isdigit()
            and len(next_parts) >= 3
            and next_parts[2] in ["connected", "disconnected", "unknown"]
        ):
          break
        if lines[j].strip().startswith("value:"):
          value_line_index = j
          break

      if value_line_index != -1:
        value_on_line = lines[value_line_index].strip().split(":", 1)[1].strip()
        value_parts = [value_on_line] if value_on_line else []
        value_line_indentation = len(lines[value_line_index]) - len(
            lines[value_line_index].lstrip()
        )
        k = value_line_index + 1
        while k < len(lines):
          next_line = lines[k]
          next_line_indentation = len(next_line) - len(next_line.lstrip())
          # if next line is more indented, it is part of the value.
          if (
              next_line.strip()
              and next_line_indentation > value_line_indentation
          ):
            value_parts.append(next_line.strip())
            k += 1
          else:
            break
        prop_value = "".join(value_parts)
        i = k  # advance main loop index
      else:
        i += 1  # no value found, just advance to next line

      connectors[current_connector_id]["props"][prop_name] = prop_value
      continue

    i += 1
  return connectors
