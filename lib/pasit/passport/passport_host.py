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

from collections.abc import Callable, MutableSequence, Sequence
import logging
import os
from typing import Any

from chromiumos.test.lab.api import pasit_host_pb2
from google.protobuf import json_format
from lib.pasit.passport import errors
from lib.pasit.passport import hid_service_client
from lib.pasit.passport import ip_9850
from lib.pasit.passport import ip_power
from lib.pasit.passport import passport_camera_service_client
from lib.pasit.passport import passport_switch_service_client
from lib.pasit.passport import passport_usb_service_client
from lib.pasit.passport import passport_video_service_client
from lib.utils import image
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
    hid_client: The client for the HID service.
    log: The logger for the PassportHost.
    usb_tester_client: The client for the USB tester service.
    video_tester_client: The client for the video tester service.
  """

  _camera_client: passport_camera_service_client.PassportCameraServiceClient = (
      None
  )
  usb_tester_client: passport_usb_service_client.PassportUsbServiceClient = None
  video_tester_client: (
      passport_video_service_client.PassportVideoServiceClient | None
  ) = None
  _switch_client: passport_switch_service_client.PassportSwitchServiceClient
  hid_client: hid_service_client.PassportHIDServiceClient | None = None
  _dut_id = None
  _devices: dict[str, pasit_host_pb2.PasitHost.Device] = {}
  _connections: dict[
      str, MutableSequence[pasit_host_pb2.PasitHost.Connection]
  ] = {}
  _ip_power_clients: dict[str, ip_power.PassportRPM] = {}

  def __init__(self, config):
    self._config = config
    self.log = mobly_logger.PrefixLoggerAdapter(
        logging.getLogger(),
        {
            mobly_logger.PrefixLoggerAdapter.EXTRA_KEY_LOG_PREFIX: (
                f'[{MOBLY_CONTROLLER_CONFIG_NAME}]'
            )
        },
    )
    # TODO: b/401048925 - remove this once the proto changes are complete
    # and the IP power switch is set in the topology. For now,
    # try the default IP and localhost:8080 for port forward dev testing
    # ignoring the error if both fail.
    dock_power = _get_dock_power('192.168.1.110', '1')
    if dock_power is None:
      dock_power = _get_dock_power('localhost:8080', '1')
    if dock_power is not None:
      logging.info(
          'Using IP power switch %s:%s for dock.',
          dock_power.power_unit_endpoint,
          dock_power.power_unit_outlet,
      )
      self._ip_power_clients['dock'] = dock_power

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
    self._connect_to_service()
    self._parse_topology()
    self._validate_topology_switches()
    self._activate_usb_testers()

  def _ensure_passport_connected(self):
    """Ensures the Passport API Service is connected."""
    if not self._switch_client:
      raise errors.PassportServiceConnectionError(
          'Cannot perform operation, Pasport client is not connected.'
      )

  def _connect_to_service(self):
    """Connects to the Passport API Service."""
    if not self.address:
      raise errors.PassportConfigError(
          'PassportHost address is not set, expected to be set in the topology'
          ' or via the service_host and service_port configs.'
      )

    self.log.info('Connecting to Passport API at address: %s' % self.address)
    self._camera_client = (
        passport_camera_service_client.PassportCameraServiceClient(self.address)
    )
    self.hid_client = hid_service_client.PassportHIDServiceClient(self.address)
    self._switch_client = (
        passport_switch_service_client.PassportSwitchServiceClient(self.address)
    )
    self.usb_tester_client = (
        passport_usb_service_client.PassportUsbServiceClient(self.address)
    )
    self.video_tester_client = (
        passport_video_service_client.PassportVideoServiceClient(self.address)
    )

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
    if len(topology_ids) == 0:
      logging.info('No USB testers are used in the topology.')
      return
    topology_id = topology_ids[0]
    passport_testers = self.usb_tester_client.get_usb_testers()
    passport_ids = [tester.id for tester in passport_testers.testers]
    if topology_id not in passport_ids:
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
    """Returns the path to the device that matches the given function."""
    current_path = []
    stack = [self._dut_id]
    visited: dict[str, bool] = {self._dut_id: True}
    children: dict[str, int] = {}

    while stack:
      current = stack.pop()
      current_path.append(current)

      if target_device_fn(self._devices[current]):
        return current_path

      for node in self._connections[current]:
        if visited.get(node.child_id, False):
          continue
        if tag and tag not in node.tags:
          continue
        stack.append(node.child_id)
        visited[node.child_id] = True
        children.setdefault(current, 0)
        children[current] += 1

      while len(current_path) > 1 and children.get(current, 0) == 0:
        current_path.pop()
        current = current_path[-1]
        children.setdefault(current, 0)
        children[current] -= 1

    raise errors.DevicePathNotFoundError(error_message)

  def _connections_in_path(
      self, path: Sequence[str]
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
      self, device_type: pasit_host_pb2.PasitHost.Device.Type,
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

  def _set_device_enabled_state_by_id(
      self, device_id: str, enable: bool, tag: str | None,
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
    self._ensure_passport_connected()
    device_path = [connection.parent_id for connection in connections]
    self.log.info(
        f'{"Activating" if enable else "Deactivating"}:  path: {device_path}',
    )
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
          self._switch_client.enable_switch(device_id, port_id)
        else:
          self._switch_client.disable_switch(device_id, port_id)
      elif (
          self._devices[device_id].type
          == pasit_host_pb2.PasitHost.Device.Type.DOCKING_STATION
      ):
        if self._ip_power_clients.get('dock'):
          self._ip_power_clients['dock'].set_ip_power_state(
              ip_power.PowerState.from_bool(enable)
          )

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
    if self._switch_client:
      self._switch_client.reset_all_switches()
    if self.usb_tester_client and self.usb_tester_client.is_open():
      self.usb_tester_client.replug()
    if self._ip_power_clients.get('dock'):
      self._ip_power_clients['dock'].set_ip_power_state(ip_power.PowerState.OFF)

  def teardown(self):
    """Tears down the PassportHost."""
    if self._switch_client:
      self._switch_client.close()
      self._switch_client = None

    if self.usb_tester_client and self.usb_tester_client.is_open():
      self.usb_tester_client.close_usb_tester()
      self.usb_tester_client = None

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
    self._ensure_passport_connected()

    resp = self._switch_client.get_switches()
    return [switch.id for switch in resp.switches]

  def get_cameras(self) -> list[str]:
    """Returns the camera IDs connected to the PassportHost."""
    self._ensure_passport_connected()
    resp = self._camera_client.get_cameras()
    return [camera.id for camera in resp.cameras]

  def capture_image(
      self,
      camera_id: str,
      log_dir: str,
      image_name_prefix: str,
      exposure_time_us: int = 0,
  ) -> None:
    """Captures an image from the specified camera and saves it.

    Image is saved to the logsdirectory with the given prefix and a timestamp.

    Args:
      camera_id: The unique ID of the camera to capture an image and
        GetAveragePixel, should be one of the camera IDs returned by
        get_cameras.
      log_dir: The directory to save the image to, should be the mobly log
        directory or a subdirectory of it.
      image_name_prefix: The prefix of the image name to use for the image.
      exposure_time_us: The exposure time in microseconds to use for the camera.
        If 0, the auto exposure setting will be used.

    Returns:
      None
    """
    # get_average_pixel will save the image if image_name_prefix is specified,
    # so call that but don't use the average pixel result.
    self.get_average_pixel(
        camera_id, log_dir, image_name_prefix, exposure_time_us
    )

  def capture_images_from_all_cameras(
      self,
      output_path: str,
      image_prefix: str,
      camera_exposure_time_us: int = 0,
  ):
    """Captures an image from each camera connected to the PassportHost.

    Args:
      output_path: The directory to save the images to.
      image_prefix: The prefix for the image file names. The actual image name
        will be {image_prefix}_camera{camera_id}.
      camera_exposure_time_us: The exposure time in microseconds to use for the
        camera. If 0, the auto exposure setting will be used.
    """
    for camera in self.get_cameras():
      logging.debug(
          'Capturing display image from %s camera %s to directory %s with'
          ' exposure time %d us',
          image_prefix,
          camera,
          output_path,
          camera_exposure_time_us,
      )
      self.capture_image(
          camera,
          output_path,
          f'{image_prefix}_camera{camera}',
          camera_exposure_time_us,
      )

  def get_average_pixel(
      self,
      camera_id: str,
      log_dir: str = '',
      image_name_prefix: str = '',
      exposure_time_us: int = 0,
  ) -> image.Color:
    """Gets the average pixel color detected by the specified camera.

    Args:
      camera_id: The unique ID of the camera to capture an image and
        GetAveragePixel.
      log_dir: The directory to save the image to, should be the mobly log
        directory or a subdirectory of it.  Must be specified if
        image_name_prefix is specified.
      image_name_prefix: The prefix of the image name to use for the image. if
        empty no image file will be saved, if specified, the image will be saved
        to logs directory with the given prefix and a timestamp.
      exposure_time_us: The exposure time in microseconds to use for the camera.
        If 0, the auto exposure setting will be used.

    Returns:
      The average pixel Color.
    """
    self._ensure_passport_connected()
    resp = self._camera_client.get_average_pixel(camera_id, exposure_time_us)
    if image_name_prefix and log_dir:
      self._save_image(resp.frame, log_dir, image_name_prefix)
    return image.Color(resp.pixel.r, resp.pixel.g, resp.pixel.b, resp.pixel.a)

  def analyze_hsv(
      self,
      camera_id: str,
      masks: dict[str, image.HSVMask],
      log_dir: str = '',
      image_name_prefix: str = '',
      exposure_time_us: int = 0,
  ) -> dict[str, float]:
    """Captures an image from the specified camera and performs HSV analysis.

    Image is saved to the logsdirectory with the given prefix and a timestamp.
    HSV analysis is performed on the image and the percentage of pixels that
    fall within the specified HSV value range is returned for each mask.

    Args:
      camera_id: The unique ID of the camera to capture an image and
        GetAveragePixel.
      masks: A dictionary of mask names to HSVMasks to compare against.
      log_dir: The directory to save the image to, should be the mobly log
        directory or a subdirectory of it.  Must be specified if
        image_name_prefix is specified.
      image_name_prefix: The prefix of the image name to use for the image. if
        empty no image file will be saved, if specified, the image will be saved
        to logs directory with the given prefix and a timestamp.
      exposure_time_us: The exposure time in microseconds to use for the camera.
        If 0, the auto exposure setting will be used.

    Returns:
      The HSV analysis results for each mask, which is a percentage value
      between 0 and 100 for the percentage of pixels that fall within the
      specified HSV value range.
    """
    self._ensure_passport_connected()
    resp = self._camera_client.analyze_hsv(camera_id, masks, exposure_time_us)
    if image_name_prefix and log_dir:
      self._save_image(resp.frame, log_dir, image_name_prefix)
    ret = {}
    for name, percentage in resp.percentage_matched.items():
      ret[name] = percentage
    return ret

  def _save_image(
      self, image_bytes: bytes, log_dir: str, image_name_prefix: str
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
        f'{image_name_prefix.replace("/", "_")}_{time_str}.jpeg',
    )
    with open(image_path, 'wb') as f:
      f.write(image_bytes)
