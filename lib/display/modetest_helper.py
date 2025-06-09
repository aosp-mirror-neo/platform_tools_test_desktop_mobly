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
  except Exception:
    return 0
