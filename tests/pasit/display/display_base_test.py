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

"""Base test for PASIT display tests."""

import enum
import logging

from lib.pasit import display_camera_mapper
from lib.pasit import display_helper
from lib.pasit import display_painter
from lib.pasit import pasit_display
from lib.pasit import pasit_test
from lib.pasit import test_policy
from lib.utils import image
from lib.utils import retry
from mobly import asserts


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


class DisplayBaseTest(pasit_test.PasitTestClass):
  """Base test for PASIT display tests."""

  display: pasit_display.PasitDisplay
  painter: display_painter.DisplayPainter
  helper: display_helper.DisplayHelper
  camera_mapper: display_camera_mapper.DisplayCameraMapper
  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_MONITOR

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.display_path_tag = None

  def setup_class(self):
    """Handle the setup for the test.

    Create PasitDisplay for the interacting with displays.
    """
    super().setup_class()
    self.display = self.create(pasit_display)
    self.painter = self.create(display_painter)

  def setup_test(self):
    """Handle the setup for the test."""
    super().setup_test()
    self.helper = display_helper.DisplayHelper(self.display)
    self.camera_mapper = display_camera_mapper.DisplayCameraMapper(
        self.passport_host,
        self.display,
        self.painter,
        self.current_test_info.output_path,
    )
    self.display_path_tag = None

  def teardown_test(self):
    """Handle the teardown for the test."""
    self.display.save_debug_info(self.current_test_info.output_path)
    self.painter.safe_clean_color_on_display()
    super().teardown_test()

  def teardown_class(self):
    """Handle the teardown for the class."""
    if hasattr(self, 'painter'):
      self.painter.cleanup()
    super().teardown_class()

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

  def setup_display_path(
      self, connection_type: ConnectionType, min_display_count: int = 1
  ):
    """Setup the display path for the test.

    This will determine the tag to use when enabling/disabling the display. And
    will skip the test if the display path cannot be determined.
    """
    try:
      self.display_path_tag = self._determine_connection_tag(connection_type)
    except (DisplayNotFoundError, DisplayPathNotFoundError) as e:
      asserts.skip(f'No display path found: {e}')
    display_cnt = self._determine_display_count(self.display_path_tag)
    if display_cnt < min_display_count:
      asserts.skip(
          f'Display count {display_cnt} is less than minimum required count'
          f' of {min_display_count} displays for this test.'
      )

  def plug_in_external_displays(self, external_display_count: int):
    """Emulate multiple external display plug in using passport.

    Skips the test if the number of monitors in the topology is less than the
    given display count.

    Args:
      external_display_count: The number of external displays to plug in.
    """
    monitor_ids = self.passport_host.get_device_ids_by_type(
        self.DEVICE_TYPE_MONITOR
    )
    asserts.skip_if(
        len(monitor_ids) < external_display_count,
        f'Expected at least {external_display_count} monitors, but'
        f' found {len(monitor_ids)}.',
    )
    for monitor_id in monitor_ids[:external_display_count]:
      logging.info('Plugging in external display %s', monitor_id)
      self.passport_host.activate_device_by_id(
          monitor_id, self.display_path_tag
      )

  def plug_in_external_display(self):
    """Emulate external display plug in using passport."""
    logging.info('Plugging in external display')
    self.passport_host.activate_device_by_type(
        self.DEVICE_TYPE_MONITOR, self.display_path_tag
    )

  def unplug_external_display(self):
    """Emulate external display unplug using passport."""
    logging.info('Unplugging external display')
    self.passport_host.deactivate_device_by_type(
        self.DEVICE_TYPE_MONITOR, self.display_path_tag
    )

  def verify_display_count(self, expected_count: int, event_to_log: str):
    """Verifies that the display count is equal to the expected count."""
    asserts.assert_equal(
        retry.retry(
            lambda: len(self.helper.get_stable_display_ids()),
            until=lambda ids_count: ids_count == expected_count,
            policy=test_policy.DisplayTestPolicy.EXPECTED_DISPLAY_COUNT_RETRY_POLICY,
            exceptions=(display_helper.DisplayIDsNotStableError,),
        ),
        expected_count,
        f'Display IDs count is not {expected_count} {event_to_log}.',
    )

  def verify_captured_color(
      self,
      camera_id: str,
      expected_color: image.NamedColor,
      camera_capture_name: str,
      failure_message: str,
  ):
    """Verifies that the camera captured the expected color.

    Fails the test if the verification fails.

    Args:
      camera_id: The camera ID to use for the verification.
      expected_color: The expected color to verify.
      camera_capture_name: Prefix for the image name to use for the capture.
      failure_message: The message to use for the assertion if the verification
        fails.
    """
    match_status = retry.retry(
        lambda: self.camera_mapper.try_match_color(
            camera_id,
            expected_color,
            f'{camera_capture_name}_from_camera{camera_id}',
        ),
        until=lambda status: status,
        policy=test_policy.DisplayTestPolicy.MATCH_COLOR_RETRY_POLICY,
    )
    asserts.assert_true(
        match_status,
        failure_message,
    )
    logging.info(
        'Camera %s detected color %s as expected',
        camera_id,
        expected_color.name,
    )

  def map_displays_to_cameras_with_retries(
      self,
  ) -> dict[pasit_display.PasitDisplay.DisplayId, str]:
    """Maps the displays to cameras with retry every 10 seconds."""
    # TODO: b/431215234 - Remove the retry once the bug is fixed.
    return retry.retry(
        self.camera_mapper.map_displays_to_cameras,
        policy=test_policy.DisplayTestPolicy.MAP_DISPLAYS_TO_CAMERAS_RETRY_POLICY,
        exceptions=(display_camera_mapper.MapDisplaysToCamerasError,),
    )
