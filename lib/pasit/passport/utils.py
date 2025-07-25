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
"""Helper functions for Passport."""

from chromiumos.test.lab.api import pasit_host_pb2

def is_edid(topology: pasit_host_pb2.PasitHost, device_id: str) -> bool:
  """Returns true if the device is an EDID device.

  Args:
    device_id: The device ID to check.
  Returns:
    True if the device is an EDID device, False otherwise.
  """
  for connection in topology.connections:
    if (
        connection.device_id == device_id
        or connection.parent_id == device_id
        and 'EDID' in connection.tags
    ):
      return True
  return False