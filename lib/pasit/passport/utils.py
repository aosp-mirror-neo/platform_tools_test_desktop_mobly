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
"""Helper functions for Passport.

These functions are used to do basic operations on the topology, without
requiring the passport host object.
"""

from chromiumos.test.lab.api import pasit_host_pb2


def is_edid(topology: pasit_host_pb2.PasitHost, device_id: str) -> bool:
  """Returns true if the device is an EDID device.

  Args:
    topology: The topology to check.
    device_id: The device ID to check.

  Returns:
    True if the device is an EDID device, False otherwise.
  """
  for connection in topology.connections:
    if 'EDID' in connection.tags and (
        connection.child_id == device_id or connection.parent_id == device_id
    ):
      return True
  return False


def is_leaf_node(topology: pasit_host_pb2.PasitHost, device_id: str) -> bool:
  """Returns true if the device is a leaf node in the topology.

  Args:
    topology: The topology to check.
    device_id: The device ID to check.

  Returns:
    True if the device is a leaf node, False otherwise.
  """
  for connection in topology.connections:
    if connection.parent_id == device_id:
      return False
  return True


def get_child_tags(
    topology: pasit_host_pb2.PasitHost,
    device_id: str,
    filter_list: list[str] | None = None,
) -> list[str | None]:
  """Returns the tags for all child nodes of the given device.

  Args:
    topology: The topology to traverse.
    device_id: The device ID to collect tags for.
    filter_list: An optional list of tags to filter the results by. If None, all
      tags will be returned.

  Returns:
    A list of tags for the device aggregated from all child nodes. If there are
    no child nodes with tags, returns [None] to indicate that the topology does
    not use tags for this device.
  """
  connections = [c for c in topology.connections if device_id == c.child_id]
  tags = []
  for connection in connections:
    for t in connection.tags:
      if not filter_list or t in filter_list:
        tags.append(t)
  if not tags:
    tags = [None]  # fallback to no tag
  return tags
