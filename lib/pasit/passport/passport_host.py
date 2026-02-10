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

"""Controller for interacting with PASIT testbed via a Passport API Host."""

from collections.abc import Callable, MutableSequence
import logging
import os
import time
from typing import Any

from chromiumos.test.lab.api import pasit_host_pb2
from chromiumos.test.lab.api import rpm_pb2
from google.protobuf import json_format
from lib.pasit.passport import errors
from lib.pasit.passport import hid_service_client
from lib.pasit.passport import ip_9850
from lib.pasit.passport import ip_power
from lib.pasit.passport import passport_camera_service_client
from lib.pasit.passport import passport_container_manager
from lib.pasit.passport import passport_switch_service_client
from lib.pasit.passport import passport_usb_service_client
from lib.pasit.passport import passport_video_service_client
from lib.utils import image
from lib.utils import constants
from mobly import logger as mobly_logger


MOBLY_CONTROLLER_CONFIG_NAME = 'PassportHost'


def create(configs: list[dict[str, Any]]) -> list['PassportHost']:
  """Creates Passport device instances."""
  if not configs:
    raise errors.PassportConfigError(f'Missing configuration {configs!r}.')
  if len(configs) > 1:
    raise errors.PassportConfigError(
        f'Multiple PassportHost configs are not supported: {configs!r}'
    )
  return [PassportHost(config) for config in configs]


def destroy(devices: list['PassportHost']) -> None:
  """Closes all created Passport device instances."""
  for device in devices:
    try:
      device.teardown()
    except Exception:  # pylint: disable=broad-except
      logging.exception('Failed to clean up properly.')


def _get_dock_power(address: str, outlet: str) -> ip_power.PassportRPM | None:
  """Returns the dock power if it is online, otherwise returns None."""
  dock_power = ip_9850.IP9850(address, outlet)
  return dock_power if dock_power.is_online() else None


class PassportHost:
  """A device that hosts a PassportHost API.

  Attributes:
    topology: The topology of the Pasit Testbed.
    address: The address of the PassportHost (in the form of hostname:port).
    log: The logger for the PassportHost.
    camera_client: The client for the camera service.
    hid_client: The client for the HID service.
    switch_client: The client for the switch service.
    usb_tester_client: The client for the USB tester service.
    video_tester_client: The client for the video tester service.
  """

  _dut_id: str
  _devices: dict[str, pasit_host_pb2.PasitHost.Device]
  _connections: dict[str, MutableSequence[pasit_host_pb2.PasitHost.Connection]]
  _ip_power_clients: dict[str, ip_power.PassportRPM]

  topology: pasit_host_pb2.PasitHost
  log: logging.LoggerAdapter

  camera_client: passport_camera_service_client.PassportCameraServiceClient
  hid_client: hid_service_client.PassportHIDServiceClient
  switch_client: passport_switch_service_client.PassportSwitchServiceClient
  usb_tester_client: passport_usb_service_client.PassportUsbServiceClient
  video_tester_client: passport_video_service_client.PassportVideoServiceClient

  def _initialize_clients(self, address: str):
    """Creates a client for the given service."""
    self.camera_client = (
        passport_camera_service_client.PassportCameraServiceClient(address)
    )
    self.hid_client = hid_service_client.PassportHIDServiceClient(address)
    self.switch_client = (
        passport_switch_service_client.PassportSwitchServiceClient(address)
    )
    self.usb_tester_client = (
        passport_usb_service_client.PassportUsbServiceClient(address)
    )
    self.video_tester_client = (
        passport_video_service_client.PassportVideoServiceClient(address)
    )

  def __init__(self, config):
    self._dut_id = ''
    self._devices = {}
    self._connections = {}
    self._ip_power_clients = {}

    self._config = config
    self.log = mobly_logger.PrefixLoggerAdapter(
        logging.getLogger(),
        {
            mobly_logger.PrefixLoggerAdapter.EXTRA_KEY_LOG_PREFIX: (
                f'[{MOBLY_CONTROLLER_CONFIG_NAME}]'
            )
        },
    )

    self._container_manager = (
        passport_container_manager.PassportContainerManager(self.log)
    )
    self._container_manager.launch_container(self._config)

    self._initialize_topology()
    self._connect_to_service()
    self._parse_topology()
    self._validate_topology_switches()
    self._activate_usb_testers()
    self._setup_ip_power_clients()

  def _initialize_topology(self):
    """Initializes the topology from the config."""
    topology = self._config.get('host_topology', None)
    if topology is None:
      # If no topology is found, that's fine. The test will need to manage the
      # switch IDs directly.
      self.log.info('No topology found, creating empty topology.')
      self.topology = pasit_host_pb2.PasitHost()
    else:
      self.topology = json_format.ParseDict(
          topology, pasit_host_pb2.PasitHost()
      )

    service_host = self._config.get('service_host', None)
    service_port = self._config.get('service_port', None)

    if service_host is not None and service_port is not None:
      # If the passport host and port are set, override the hostname in the
      # passport device.
      self.log.debug(
          'Overriding hostname "%s" with switch host and port: %s:%s',
          self.topology.hostname,
          service_host,
          service_port,
      )
      self.topology.hostname = f'{service_host}:{service_port}'  # pylint: disable=bad-whitespace

    self.log.debug('PassportHost topology: %s' % self.topology)

  def _connect_to_service(self):
    """Connects to the Passport API Service."""
    if not self.address:
      raise errors.PassportConfigError(
          'PassportHost address is not set, expected to be set in the topology'
          ' or via the service_host and service_port configs.'
      )

    self.log.info('Connecting to Passport API at address: %s' % self.address)
    self._initialize_clients(self.address)

  def _parse_topology(self):
    """Parses the topology and stores the devices and connections."""
    for device in self.topology.devices:
      self._devices[device.id] = device
      if device.type == pasit_host_pb2.PasitHost.Device.Type.DUT:
        self._dut_id = device.id
    for connection in self.topology.connections:
      for key in [connection.parent_id, connection.child_id]:
        if key not in self._devices:
          raise errors.PassportConfigError(
              f'Connection {connection} has a parent or child device "{key}"'
              ' that is not in the topology.'
          )
        if key in self._connections:
          self._connections[key].append(connection)
        else:
          self._connections[key] = [connection]

  def _validate_topology_switches(self):
    """Validates the topology switches."""
    connected_switches = self.get_switch_ids()
    for switch in connected_switches:
      if not any(
          device.id.casefold() == switch.casefold()
          for device in self.topology.devices
      ):
        logging.warning(
            'Switch %s is connected, but is not in the topology.', switch
        )
    for device in self.topology.devices:
      if device.type == pasit_host_pb2.PasitHost.Device.Type.SWITCH_FIXTURE:
        if not any(
            device.id.casefold() == switch.casefold()
            for switch in connected_switches
        ):
          raise errors.PassportConfigError(
              f'Switch {device.id} is not connected, but is in the topology.'
          )

  def _setup_ip_power_clients(self):
    """Sets up the IP power clients."""
    for device in self.topology.devices:
      if device.rpm.present:
        if not device.rpm.type == rpm_pb2.RPMType.RPM_TYPE_IP9850:
          raise errors.PassportConfigError('Only IP9850 RPMs are supported.')
        logging.info('Setting up IP power client for: %s', device.id)
        endpoint = f'{device.rpm.power_unit_hostname.address}'
        if device.rpm.power_unit_hostname.port:
          endpoint = f'{endpoint}:{device.rpm.power_unit_hostname.port}'
        self._ip_power_clients[device.id] = ip_9850.IP9850(
            endpoint, device.rpm.power_unit_outlet
        )
        if not self._ip_power_clients[device.id].is_online():
          raise errors.PassportRPMError(
              f'IP power client for device {device.id}  at {endpoint} is not'
              ' online',
          )

  def _activate_usb_testers(self):
    """Acivate the topology usb tester.

    Raises:
      PassportConfigError: if there are more than 1 usb tester in the topology
        or if the tester was in the open state.
      PassportConfigError: if there is a tester specified in the topology but it
        is not controlled by the current instance of passport host.
    """
    topology_ids = [
        device.id
        for device in self.topology.devices
        if device.type == pasit_host_pb2.PasitHost.Device.Type.USB_TESTER
    ]
    if len(topology_ids) > 1:
      raise errors.PassportConfigError(
          f'More than 1 usb tester found, found {len(topology_ids)} testers.'
      )
    if not topology_ids:
      logging.info('No USB testers are used in the topology.')
      return
    topology_id = topology_ids[0]
    passport_testers = self.usb_tester_client.get_usb_testers()
    passport_ids = [tester.id for tester in passport_testers.testers]
    if topology_id.upper() not in passport_ids:
      raise errors.PassportConfigError(
          f'Topology tester {topology_id} is not controlled by passport host.'
      )
    self.usb_tester_client.open_usb_tester(topology_id)

  def _connections_to_device_by_type(
      self,
      device_type: pasit_host_pb2.PasitHost.Device.Type,
      tag: str | None,
  ) -> MutableSequence[pasit_host_pb2.PasitHost.Connection]:
    """Returns the path to the device with the given device type."""
    devices = self._path_to_device(
        lambda device: device.type == device_type,
        tag,
        'Passport was unable to find any connections to any devices of type:'
        f' {pasit_host_pb2.PasitHost.Device.Type.Name(device_type)} in the'
        ' topology.',
    )
    return self._connections_in_path(devices)

  def _connections_to_device_by_id(
      self,
      device_id: str,
      tag: str | None,
  ) -> MutableSequence[pasit_host_pb2.PasitHost.Connection]:
    """Returns the path to the device with the given device ID."""
    devices = self._path_to_device(
        lambda device: device.id == device_id,
        tag,
        'Passport was unable to find any connections to any devices with ID:'
        f' {device_id} in the topology.',
    )
    return self._connections_in_path(devices)

  def _path_to_device(
      self,
      target_device_fn: Callable[[pasit_host_pb2.PasitHost.Device], bool],
      tag: str | None,
      error_message: str,
  ) -> MutableSequence[str]:
    """Returns the first found path to the device that matches the given function."""
    paths = self._paths_to_device(target_device_fn, tag)
    if not paths:
      raise errors.DevicePathNotFoundError(error_message)
    return paths[0]

  def _paths_to_device(
      self,
      target_device_fn: Callable[[pasit_host_pb2.PasitHost.Device], bool],
      tag: str | None,
  ) -> MutableSequence[MutableSequence[str]]:
    """Returns all paths to the device(s) that match the given function/tag."""
    paths: list[list[str]] = []

    # Helper function to perform the recursive search
    def find_paths_recursive(current_node_id: str, current_path: list[str]):
      # Check if the current node is a target
      if target_device_fn(self._devices[current_node_id]):
        # Add a copy of the found path to our results
        paths.append(list(current_path))

      # Explore neighbors sorting by child ids to ensure deterministic results
      for connection in sorted(
          self._connections.get(current_node_id, []),
          key=lambda connection: connection.child_id,
      ):
        child_id = connection.child_id
        # 1. Check for tag match
        if tag and tag not in connection.tags:
          continue
        # 2. Prevent cycles by ensuring we don't revisit a node in the current path
        if child_id in current_path:
          continue
        # 3. Recurse with the updated path
        find_paths_recursive(child_id, current_path + [child_id])

    # Start the search from the root DUT
    find_paths_recursive(self._dut_id, [self._dut_id])
    return paths

  def _connections_in_path(
      self, path: MutableSequence[str]
  ) -> MutableSequence[pasit_host_pb2.PasitHost.Connection]:
    """Returns the connections in the given path."""
    connections = []
    for i in range(len(path) - 1):
      parent_id = path[i]
      child_id = path[i + 1]
      for connection in self._connections[parent_id]:
        if child_id == connection.child_id:
          connections.append(connection)
          break
    return connections

  def is_device_type_present(
      self,
      device_type: pasit_host_pb2.PasitHost.Device.Type,
      tag: str | None,
  ) -> bool:
    """Returns True if the device type is present in the topology.

    Args:
      device_type: The device type to check.
      tag: Optional tag to filter the device path by, will only consider paths
        where every connection in the path has this tag.
    """
    try:
      self._connections_to_device_by_type(device_type, tag)
      return True
    except errors.DevicePathNotFoundError:
      return False

  def get_device_count_by_type(
      self,
      device_type: pasit_host_pb2.PasitHost.Device.Type,
  ) -> int:
    """Returns the number of devices of the given type in the topology."""
    return len([
        device for device in self.topology.devices if device.type == device_type
    ])

  def get_device_ids_by_type(
      self,
      device_type: pasit_host_pb2.PasitHost.Device.Type,
  ) -> list[str]:
    """Returns the device IDs of the given type in the topology."""
    return [
        device.id
        for device in self.topology.devices
        if device.type == device_type
    ]

  def get_paths_by_type(
      self,
      device_type: pasit_host_pb2.PasitHost.Device.Type,
      tag: str | None,
  ) -> MutableSequence[MutableSequence[str]]:
    """Returns all paths of devices of the given type in the topology.

    Args:
      device_type: The device type to check.
      tag: Optional tag to filter the device path by, will only consider paths
        where every connection in the path has this tag.

    Returns:
      A list of paths of devices of the given type in the topology.
    """
    return self._paths_to_device(
        lambda device: device.type == device_type,
        tag,
    )

  def _set_device_enabled_state_by_id(
      self,
      device_id: str,
      enable: bool,
      tag: str | None,
  ) -> None:
    """Activates or deactivates the device with the given device ID."""
    connections = self._connections_to_device_by_id(device_id, tag)
    self._set_device_enabled_state_by_path(connections, enable)

  def _set_device_enabled_state_by_type(
      self,
      device_type: pasit_host_pb2.PasitHost.Device.Type,
      enable: bool,
      tag: str | None,
  ) -> None:
    """Activates or deactivates the device with the given device type."""
    connections = self._connections_to_device_by_type(device_type, tag)
    self._set_device_enabled_state_by_path(connections, enable)

  def _set_device_enabled_state_by_path(
      self, connections: MutableSequence[Any], enable: bool
  ) -> None:
    """Activates or deactivates the device with the given connection path."""
    if not connections:
      self.log.warning(
          'No connections found, skipping setting enabled state.'
      )
      return
    device_path = [connection.parent_id for connection in connections]
    device_path.append(connections[-1].child_id)
    self.log.info(
        f'{"Activating" if enable else "Deactivating"}:  path: {device_path}',
    )
    ip_power_set = False
    for device_id in device_path:
      # TODO: b/442614713 - decide if this change should be permanent or if we
      # may eventually want to support variants with different order of
      # operations, to catch bugs related to that.
      if self._ip_power_clients.get(device_id):
        self._ip_power_clients[device_id].set_ip_power_state(
            ip_power.PowerState.from_bool(enable)
        )
        ip_power_set = True
    if ip_power_set:
      time.sleep(1)
    for connection in connections:
      device_id = connection.parent_id
      port_id = connection.parent_port
      if (
          self._devices[device_id].type
          == pasit_host_pb2.PasitHost.Device.Type.SWITCH_FIXTURE
      ):
        self.log.debug(
            'Setting switch %s %sto %s',
            device_id,
            f'port {port_id} ' if port_id else '',
            'enabled' if enable else 'disabled',
        )
        if enable:
          self.switch_client.enable_switch(device_id, port_id)
        else:
          self.switch_client.disable_switch(device_id, port_id)

  @property
  def address(self) -> str:
    """Returns the hostname of the PassportHost."""
    return self.topology.hostname

  def reset(self):
    """Resets the PassportHost.

    Raises:
      DevicePathNotFoundError: If the Passport was unable to reset the connected
        switches.
      PassportIPPowerError: If the Passport was unable to reset the IP power
        switches.
    """
    self.switch_client.reset_all_switches()
    for device in self.topology.devices:
      if (
          device.type == pasit_host_pb2.PasitHost.Device.Type.SWITCH_FIXTURE
          and device.switch_fixture_details is not None
          and device.switch_fixture_details.initial_state_enabled
      ):
        port_id = device.switch_fixture_details.initial_port
        self.log.info(
            'Setting switch %s %sto enabled on reset',
            device.id,
            f'port {port_id} ' if port_id else '',
        )
        self.switch_client.enable_switch(device.id, port_id)

    if self.usb_tester_client.is_open():
      self.usb_tester_client.replug()
    for ip_power_client in self._ip_power_clients.values():
      ip_power_client.set_ip_power_state(ip_power.PowerState.OFF)
    if self._ip_power_clients:
      # delay to allow time for the IP power switches to turn off and any
      # capacitors in chargers to discharge, without this flaky behavior may
      # occur with docks
      time.sleep(2)

  def teardown(self):
    """Tears down the PassportHost."""
    self.camera_client.close()
    self.hid_client.close_channel()

    self.switch_client.close()

    if self.usb_tester_client.is_open():
      self.usb_tester_client.close_usb_tester()

    if self.video_tester_client.is_open():
      self.video_tester_client.close_video_tester()

    self._container_manager.teardown()

  def activate_device_by_type(
      self,
      device_type: pasit_host_pb2.PasitHost.Device.Type,
      tag: str | None = None,
  ) -> None:
    """Activates the device with the given device type.

    Args:
      device_type: The device type to activate.
      tag: Optional tag to filter the device path by, will only consider paths
        where every connection in the path has this tag.

    Raises:
      DevicePathNotFoundError: If the Passport was unable to find the device
        with the given device type.
      PassportIPPowerError: If the Passport was unable to set the IP power
        switch state.
      PassportSwitchError: If the Passport was unable to set the switch state.
    """
    self._set_device_enabled_state_by_type(device_type, True, tag)

  def deactivate_device_by_type(
      self,
      device_type: pasit_host_pb2.PasitHost.Device.Type,
      tag: str | None = None,
  ) -> None:
    """Deactivates the device with the given device type.

    Args:
      device_type: The device type to deactivate.
      tag: Optional tag to filter the device path by, will only consider paths
        where every connection in the path has this tag.

    Raises:
      DevicePathNotFoundError: If the Passport was unable to find the device
        with the given device type.
      PassportIPPowerError: If the Passport was unable to set the IP power
        switch state.
      PassportSwitchError: If the Passport was unable to set the switch state.
    """
    self._set_device_enabled_state_by_type(device_type, False, tag)

  def activate_device_by_id(
      self, device_id: str, tag: str | None = None
  ) -> None:
    """Activates the device with the given device ID.

    Args:
      device_id: The device ID to activate.
      tag: Optional tag to filter the device path by, will only consider paths
        where every connection in the path has this tag.

    Raises:
      PassportSwitchError: If the Passport was unable to set the switch state.
    """
    self._set_device_enabled_state_by_id(device_id, True, tag)

  def deactivate_device_by_id(
      self, device_id: str, tag: str | None = None
  ) -> None:
    """Deactivates the device with the given device ID.

    Args:
      device_id: The device ID to deactivate.
      tag: Optional tag to filter the device path by, will only consider paths
        where every connection in the path has this tag.

    Raises:
      PassportSwitchError: If the Passport was unable to set the switch state.
    """
    self._set_device_enabled_state_by_id(device_id, False, tag)

  def get_switch_ids(self) -> MutableSequence[str]:
    """Returns the switch IDs connected to the PassportHost.

    Raises:
      PassportSwitchClientError: If the Passport was unable to get the switches.
    """

    resp = self.switch_client.get_switches()
    return [switch.id for switch in resp.switches]

  def get_cameras(self) -> list[str]:
    """Returns the camera IDs connected to the PassportHost."""
    resp = self.camera_client.get_cameras()
    return [camera.id for camera in resp.cameras]

  def get_device_by_id(self, device_id: str) -> pasit_host_pb2.PasitHost.Device:
    """Returns the device with the given device ID."""
    return self._devices[device_id]

  def capture_image(
      self,
      camera_id: str,
      log_dir: str,
      image_name_suffix: str,
      exposure_time_us: int = 0,
  ) -> None:
    """Captures an image from the specified camera and saves it.

    Image is saved to the logsdirectory with the given suffix and a timestamp.

    Args:
      camera_id: The unique ID of the camera to capture an image and
        GetAveragePixel, should be one of the camera IDs returned by
        get_cameras.
      log_dir: The directory to save the image to, should be the mobly log
        directory or a subdirectory of it.
      image_name_suffix: The suffix of the created image filename.
      exposure_time_us: The exposure time in microseconds to use for the camera.
        If 0, the auto exposure setting will be used.

    Returns:
      None
    """
    # get_average_pixel will save the image if image_name_suffix is specified,
    # so call that but don't use the average pixel result.
    self.get_average_pixel(
        camera_id, log_dir, image_name_suffix, exposure_time_us
    )

  def capture_images_from_all_cameras(
      self,
      output_path: str,
      image_suffix: str,
      camera_exposure_time_us: int = 0,
  ):
    """Captures an image from each camera connected to the PassportHost.

    Args:
      output_path: The directory to save the images to.
      image_suffix: The suffix for the image file names. The actual image name
        will be {timestamp}_{image_suffix}_camera{camera_id}.
      camera_exposure_time_us: The exposure time in microseconds to use for the
        camera. If 0, the auto exposure setting will be used.
    """
    for camera in self.get_cameras():
      logging.debug(
          'Capturing display image from %s camera %s to directory %s with'
          ' exposure time %d us',
          image_suffix,
          camera,
          output_path,
          camera_exposure_time_us,
      )
      self.capture_image(
          camera,
          output_path,
          f'{image_suffix}_camera{camera}',
          camera_exposure_time_us,
      )

  def get_average_pixel(
      self,
      camera_id: str,
      log_dir: str = '',
      image_name_suffix: str = '',
      exposure_time_us: int = 0,
  ) -> image.Color:
    """Gets the average pixel color detected by the specified camera.

    Args:
      camera_id: The unique ID of the camera to capture an image and
        GetAveragePixel.
      log_dir: The directory to save the image to, should be the mobly log
        directory or a subdirectory of it.  Must be specified if
        image_name_suffix is specified.
      image_name_suffix: The suffix of the image name to use for the image. If
        specified, the image will be saved to logs directory with the timestamp
        followed by the suffix.
      exposure_time_us: The exposure time in microseconds to use for the camera.
        If 0, the auto exposure setting will be used.

    Returns:
      The average pixel Color.
    """
    resp = self.camera_client.get_average_pixel(camera_id, exposure_time_us)
    if image_name_suffix and log_dir:
      self._save_image(resp.frame, log_dir, image_name_suffix)
    return image.Color(resp.pixel.r, resp.pixel.g, resp.pixel.b, resp.pixel.a)

  def analyze_hsv(
      self,
      camera_id: str,
      masks: dict[str, image.HSVMask],
      log_dir: str = '',
      image_name_suffix: str = '',
      exposure_time_us: int = 0,
  ) -> dict[str, float]:
    """Captures an image from the specified camera and performs HSV analysis.

    Image is saved to the logsdirectory with the given suffix and a timestamp.
    HSV analysis is performed on the image and the percentage of pixels that
    fall within the specified HSV value range is returned for each mask.

    Args:
      camera_id: The unique ID of the camera to capture an image and
        GetAveragePixel.
      masks: A dictionary of mask names to HSVMasks to compare against.
      log_dir: The directory to save the image to, should be the mobly log
        directory or a subdirectory of it.  Must be specified if
        image_name_suffix is specified.
      image_name_suffix: The suffix of the image name to use for the image. If
        specified, the image will be saved to logs directory with the timestamp
        followed by the suffix.
      exposure_time_us: The exposure time in microseconds to use for the camera.
        If 0, the auto exposure setting will be used.

    Returns:
      The HSV analysis results for each mask, which is a percentage value
      between 0 and 100 for the percentage of pixels that fall within the
      specified HSV value range.
    """
    resp = self.camera_client.analyze_hsv(camera_id, masks, exposure_time_us)
    if image_name_suffix and log_dir:
      self._save_image(resp.frame, log_dir, image_name_suffix)
    return {entry.key: entry.value for entry in resp.percentage_matched}

  def _save_image(
      self, image_bytes: bytes, log_dir: str, image_name_suffix: str
  ) -> None:
    """Saves the image to the logs directory."""
    if not image_bytes:
      self.log.warning(
          'No image bytes received, image will not be saved to %s.',
          log_dir,
      )
      return
    time_str = mobly_logger.get_log_file_timestamp()
    image_path = os.path.join(
        log_dir,
        f'{time_str}_{image_name_suffix.replace("/", "_")}.jpeg',
    )
    with open(image_path, 'wb') as f:
      f.write(image_bytes)

  def save_topology_diagram(self, log_dir: str) -> None:
    try:
      graph_content = '''{
        node [shape=plain];
        ranksep = 1.2;
      '''
      for device in self.topology.devices:
        ports = ''
        for connection in self.topology.connections:
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
      for connection in self.topology.connections:
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

      topology_html = constants.HTML_GRAPH_TEMPLATE.format(content=graph_content)

      with open(os.path.join(log_dir, "topology.html"), 'w') as f:
        f.write(topology_html)
    except Exception as e:
      # Don't fail the test if we can't save the image.
      self.log.exception(e)
