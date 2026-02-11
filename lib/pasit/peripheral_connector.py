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

from collections.abc import MutableSequence
import enum

from chromiumos.test.lab.api import pasit_host_pb2
from lib.pasit.passport import passport_host


def get_device_type_name(
    device_type: pasit_host_pb2.PasitHost.Device.Type,
) -> str:
  return (
      pasit_host_pb2.PasitHost.Device.Type.Name(device_type)
      if device_type
      else ''
  )


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


class PeripheralNotFoundError(Exception):
  """Error when the peripheral is not found in the topology."""

  def __init__(self, peripheral_type: pasit_host_pb2.PasitHost.Device.Type):
    super().__init__(
        f'No {get_device_type_name(peripheral_type)} found in the topology.'
    )
    self.peripheral_type = peripheral_type


class PeripheralPathNotFoundError(Exception):
  """Error when the path for the peripheral is not found in the topology."""

  def __init__(self, connection_type: ConnectionType):
    super().__init__(
        f'Peripheral path {connection_type.name} not found in topology.'
    )
    self.connection_type = connection_type


class PeripheralCountMismatchError(Exception):
  """Error when the peripheral count is less than the minimum required count."""

  def __init__(self, peripheral_count: int, min_peripheral_count: int):
    super().__init__(
        f'Peripheral count {peripheral_count} is less than minimum required'
        f' count of {min_peripheral_count} peripherals for this test.'
    )
    self.peripheral_count = peripheral_count
    self.min_peripheral_count = min_peripheral_count


class PeripheralConnector:
  """Helper class for connecting and disconnecting peripherals."""

  def __init__(self, passport: passport_host.PassportHost):
    self.passport_host = passport

  def _determine_connection_tag(
      self,
      peripheral_type: pasit_host_pb2.PasitHost.Device.Type,
      connection_type: ConnectionType,
  ) -> ConnectionTag | None:
    """Determine the connection tag to use for the test.

    This will account for both tagged and untagged connections.  It defaults by
    searching for a peripheral with a tag, and if it is not found, it will
    attempt to infer the path type of an untagged peripheral.

    Args:
      peripheral_type: The type of peripheral to get the connection tag for.
      connection_type: The type of connection to use for the peripheral.

    Returns:
      The connection tag to use for the peripheral.
    Raises:
      PeripheralNotFoundError: If the peripheral type is not found in the
        topology.
      PeripheralPathNotFoundError: If the path for the peripheral is not found
      in the topology.
    """
    # Check if the peripheral is present in the topology at all.
    if not self.passport_host.is_device_type_present(peripheral_type, None):
      raise PeripheralNotFoundError(peripheral_type)

    # get the connection tag that corresponds to the connection type
    connection_tag = CONNECTION_TAG_BY_CONNECTION_TYPE[connection_type]
    # check if the peripheral is present in the topology with the connection tag
    if self.passport_host.is_device_type_present(
        peripheral_type, connection_tag
    ):
      return connection_tag

    # If there are no tagged paths, attempt to infer the path type (dock or
    # dockless), by checking whether or not a peripheral is connected via a
    # dock. If there are different paths (some with dock, some without) in the
    # topology, then raise an error.
    all_paths = self.passport_host.get_paths_by_type(peripheral_type, None)
    path_types = {self._is_dock_path(path) for path in all_paths}
    if len(path_types) != 1:
      raise PeripheralPathNotFoundError(connection_type)

    is_dock_path = path_types.pop()
    if connection_type == ConnectionType.DOCK and is_dock_path:
      # using no tag is the same as using the DOCK tag if all paths contain a
      # dock.
      return None
    if connection_type == ConnectionType.DOCKLESS and not is_dock_path:
      # using no tag is the same as using the DOCKLESS tag if no paths contain
      # a dock.
      return None

    raise PeripheralPathNotFoundError(connection_type)

  def _is_dock_path(self, path: MutableSequence[str]) -> bool:
    """Determine if the path contains a dock."""
    for node in path:
      if (
          self.passport_host.get_device_by_id(node).type
          == pasit_host_pb2.PasitHost.Device.Type.DOCKING_STATION
      ):
        return True
    return False

  def get_peripheral_ids(
      self,
      peripheral_type: pasit_host_pb2.PasitHost.Device.Type,
      connection_tag: ConnectionTag | None,
  ) -> list[str]:
    """Get the unique peripheral IDs for the given peripheral type and tag.

    Args:
      peripheral_type: The type of peripheral to get the IDs for.
      connection_tag: The connection tag to use for the peripherals.

    Returns:
      A sorted list of unique peripheral IDs.
    """
    paths = self.passport_host.get_paths_by_type(
        peripheral_type, connection_tag
    )
    # The number of unique peripherals is the number of unique endpoints in the
    # paths.
    return sorted(list(set({path[-1] for path in paths if path})))

  def _determine_peripheral_count(
      self,
      peripheral_type: pasit_host_pb2.PasitHost.Device.Type,
      connection_tag: ConnectionTag | None,
  ) -> int:
    """Determine the peripheral count to use for the test.

    Determines the number of peripherals in the topology that are with the given
    connection tag.  For instance if the connection tag is DOCK, then this will
    return the number of unique peripherals that are in the topology and tagged
    as DOCK.

    Args:
      peripheral_type: The type of peripheral to determine the count for.
      connection_tag: The connection tag to use for determining the peripherals.

    Returns:
      The number of peripherals in the topology that have the given tag.
    """
    return len(self.get_peripheral_ids(peripheral_type, connection_tag))

  def get_peripheral_path_tag(
      self,
      peripheral_type: pasit_host_pb2.PasitHost.Device.Type,
      connection_type: ConnectionType,
      min_peripheral_count: int = 1,
  ) -> ConnectionTag | None:
    """Get the connection tag to use for the peripheral path.

    This will determine the tag to use when enabling/disabling the peripheral.
    And will skip the test if the peripheral path cannot be determined.

    Args:
      peripheral_type: The type of peripheral to get the connection tag for.
      connection_type: The type of connection to use for the peripheral.
      min_peripheral_count: The minimum number of peripherals that are required
        to be present in the topology.

    Returns:
      The connection tag to use for the test.
    Raises:
      PeripheralNotFoundError: If the peripheral type is not found in the
        topology.
      PeripheralPathNotFoundError: If the path for the peripheral is not found
      in the topology.
      PeripheralCountMismatchError: If the peripheral count is less than the
      minimum required count.
    """
    path_tag = self._determine_connection_tag(peripheral_type, connection_type)
    peripheral_count = self._determine_peripheral_count(
        peripheral_type, path_tag
    )
    if peripheral_count < min_peripheral_count:
      raise PeripheralCountMismatchError(peripheral_count, min_peripheral_count)
    return path_tag
