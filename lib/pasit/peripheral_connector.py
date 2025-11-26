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

"""Helper class for connecting and disconnecting peripherals."""

import enum

from chromiumos.test.lab.api import pasit_host_pb2
from lib.pasit.passport import passport_host


class ConnectionType(enum.Enum):
  """Enum for the types of connection in the topology.

  Connection type is determined by the connection path in the topology. For
  example, a peripheral may be connected directly (without a dock) and not
  marked with a 'DOCKLESS' tag (for example, USB-A peripherals).
  """

  ANY = (
      enum.auto()
  )  # Used for tests where peripherals can be connected via any path.
  DOCK = enum.auto()
  DOCKLESS = enum.auto()
  DAISY_CHAIN = enum.auto()


class ConnectionTag(enum.StrEnum):
  """Enum for the different device connection tags.

  Represents the connection tags in the topology. For example, if a peripheral
  is connected via a dock, but marked with a 'DOCKLESS' tag - the connection tag
  would be DOCKLESS.
  """

  DOCK = 'DOCK'
  DOCKLESS = 'DOCKLESS'
  DAISY_CHAIN = 'DAISY_CHAIN'


# Direct mapping from connection type to connection tag. This doesn't appy if
# the topology connections are not marked with tags.
CONNECTION_TAG_BY_CONNECTION_TYPE: dict[
    ConnectionType, ConnectionTag | None
] = {
    ConnectionType.ANY: None,
    ConnectionType.DOCK: ConnectionTag.DOCK,
    ConnectionType.DOCKLESS: ConnectionTag.DOCKLESS,
    ConnectionType.DAISY_CHAIN: ConnectionTag.DAISY_CHAIN,
}


class DisplayNotFoundError(Exception):
  """Error when the display is not found in the topology."""

  def __init__(self):
    super().__init__('No display found in the topology.')


class DisplayPathNotFoundError(Exception):
  """Error when the display path is not found in the topology."""

  def __init__(self, connection_type: ConnectionType):
    super().__init__(f'Display path {connection_type} not found in topology.')
    self.connection_type = connection_type


class DisplayCountMismatchError(Exception):
  """Error when the display count is less than the minimum required count."""

  def __init__(self, display_count: int, min_display_count: int):
    super().__init__(
        f'Display count {display_count} is less than minimum required'
        f' count of {min_display_count} displays for this test.'
    )
    self.display_count = display_count
    self.min_display_count = min_display_count


class PeripheralConnector:
  """Helper class for connecting and disconnecting peripherals."""

  DEVICE_TYPE_MONITOR = pasit_host_pb2.PasitHost.Device.Type.MONITOR
  DEVICE_TYPE_DOCK = pasit_host_pb2.PasitHost.Device.Type.DOCKING_STATION

  def __init__(self, passport: passport_host.PassportHost):
    self.passport_host = passport

  def _determine_connection_tag(
      self,
      connection_type: ConnectionType,
  ) -> ConnectionTag | None:
    """Determine the connection tag to use for the test.

    This will account for both tagged and untagged connections.  It defaults by
    searching for a display with a tag, and if it is not found, it will attempt
    to infer the path type of an untagged display.

    Args:
      connection_type: The type of connection to use for the display.

    Returns:
      The connection tag to use for the display.
    Raises:
      DisplayNotFoundError: If the display is not found in the topology.
      DisplayPathNotFoundError: If the display path is not found in the
      topology.
    """
    # Check if the display is present in the topology at all.
    if not self.passport_host.is_device_type_present(
        self.DEVICE_TYPE_MONITOR, None
    ):
      raise DisplayNotFoundError()

    # get the connection tag that corresponds to the connection type
    connection_tag = CONNECTION_TAG_BY_CONNECTION_TYPE[connection_type]
    # Check if the display is present in the topology with the connection tag.
    if self.passport_host.is_device_type_present(
        self.DEVICE_TYPE_MONITOR, connection_tag
    ):
      return connection_tag

    # If there are no tagged paths, attempt to infer the path type (dock or
    # dockless), by checking whether or not a display is connected via a
    # dock. If there are different paths (some with dock, some without) in the
    # topology, then raise an error.
    paths = self.passport_host.get_paths_by_type(self.DEVICE_TYPE_MONITOR, None)
    dock_path_count = 0
    for path in paths:
      for node in path:
        if (
            self.passport_host.get_device_by_id(node).type
            == self.DEVICE_TYPE_DOCK
        ):
          dock_path_count += 1

    if connection_type == ConnectionType.DOCK and dock_path_count == len(paths):
      # using no tag is the same as using the DOCK tag if all paths contain a
      # dock.
      return None
    if connection_type == ConnectionType.DOCKLESS and dock_path_count == 0:
      # using no tag is the same as using the DOCKLESS tag if no paths contain
      # a dock.
      return None

    raise DisplayPathNotFoundError(connection_type)

  def _determine_display_count(
      self,
      connection_tag: ConnectionTag | None,
  ) -> int:
    """Determine the display count to use for the test.

    Determines the number of displays in the topology that are with the given
    connection tag.  For instance if the connection tag is DOCK, then this will
    return the number of unique displays that are in the topology and tagged
    as DOCK.

    Args:
      connection_tag: The tag to use for determining the display count.

    Returns:
      The number of displays in the topology that have the given tag.
    """
    displays = self.passport_host.get_device_ids_by_type(
        self.DEVICE_TYPE_MONITOR
    )
    paths = self.passport_host.get_paths_by_type(
        self.DEVICE_TYPE_MONITOR, connection_tag
    )
    # Filter so only displays that are in the list of paths are included.
    # This is to ensure we have the correct number of displays for the a given
    # path tag. If the display device ID is anywehere in the path, then it is
    # considered to be reachable for enabling/disabling by the path tag.
    valid_displays = [
        display_id
        for display_id in displays
        if any(display_id in path for path in paths)
    ]
    return len(valid_displays)

  def get_display_path_tag(
      self, connection_type: ConnectionType, min_display_count: int = 1
  ) -> ConnectionTag | None:
    """Setup the display path for the test.

    This will determine the tag to use when enabling/disabling the display. And
    will skip the test if the display path cannot be determined.

    Args:
      connection_type: The type of connection to use for the display.
      min_display_count: The minimum number of displays required for the test.

    Returns:
      The connection tag to use for the display.

    Raises:
      DisplayNotFoundError: If the display is not found in the topology.
      DisplayPathNotFoundError: If the display path is not found in the
      topology.
      DisplayCountMismatchError: If the display count is less than the minimum
      required count.
    """
    display_path_tag = self._determine_connection_tag(connection_type)
    display_cnt = self._determine_display_count(display_path_tag)
    if display_cnt < min_display_count:
      raise DisplayCountMismatchError(display_cnt, min_display_count)
    return display_path_tag
