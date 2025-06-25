"""Client for the Passport API handling the HID Service functionality."""

from chromiumos.test.lab.api.passport import hid_service_pb2
from chromiumos.test.lab.api.passport import hid_service_pb2_grpc
from google.protobuf import duration_pb2
import grpc


class PassportHIDClientError(Exception):
  """Camera service RPC error for non-state-modifying requests."""


class PassportHIDServiceClient:
  """Client for the Passport API handling the Camera Service functionality."""

  def __init__(self, server_address: str):
    """Initializes the PassportHIDServiceClient.

    Args:
      server_address: The address of the Passport API server, e.g.
        'localhost:8300'.
    """

    # instantiate the channel
    self.channel = grpc.insecure_channel(server_address)

    # bind the client and the server
    self.stub = hid_service_pb2_grpc.HIDServiceStub(self.channel)

  def close(self):
    """Closes the PassportHIDServiceClient."""
    self.channel.close()

  def get_hid_devices(self) -> list[str]:
    """Gets the HID devices connected to the host.

    Returns:
      The list of HID devices connected to the host, string representation of
      the HID device is just the ID of the HID device that should be used in
      the other HID service methods.
    Raises:
      PassportHIDClientError: If the RPC fails.
    """
    try:
      resp = self.stub.GetHIDDevices(hid_service_pb2.GetHIDDevicesRequest())
      return [device.id for device in resp.devices]
    except grpc.RpcError as e:
      raise PassportHIDClientError(
          'Failed to get HID devices from Passport.'
      ) from e

  def open(self, device_id: str):
    """Initialize the HID device so it is ready to send HID events

    Args:
      device_id: The ID of the HID device to initialize.

    Raises:
      PassportHIDClientError: If the RPC fails.
    """
    try:
      self.stub.InitHIDDevice(
          hid_service_pb2.InitHIDDeviceRequest(device_id=device_id)
      )
    except grpc.RpcError as e:
      raise PassportHIDClientError(
          f'Failed to initialize HID device {device_id}.'
      ) from e

  def close(self, device_id: str):
    """Close the HID device when finished using it to send HID events

    Args:
      device_id: The ID of the HID device to close.

    Raises:
      PassportHIDClientError: If the RPC fails.
    """
    try:
      self.stub.CloseHIDDevice(
          hid_service_pb2.CloseHIDDeviceRequest(device_id=device_id)
      )
    except grpc.RpcError as e:
      raise PassportHIDClientError(
          f'Failed to close HID device {device_id}.'
      ) from e

  def send_keypress(
      self, device_id: str, keys: list[str], duration_ms: int = 100
  ):
    """Send a keyboard keypress event to the DUT through the HID emulator

    Args:
      device_id: The ID of the HID device to send the keypress to.
      keys: The list of keys to send, if multiple keys are provided they will be
        sent as a single keypress event with the keys pressed at the same time.
      duration_ms: The duration of the keypress in milliseconds.

    Raises:
      PassportHIDClientError: If the RPC fails.
      ValueError: If the duration is not greater than 0.
    """
    if duration_ms <= 0:
      raise ValueError(f'Duration must be greater than 0, got {duration_ms}.')
    duration = duration_pb2.Duration()
    duration.FromMilliseconds(duration_ms)
    try:
      self.stub.KeyboardAction(
          hid_service_pb2.KeyboardActionRequest(
              device_id=device_id,
              keys=keys,
              press_and_release=hid_service_pb2.KeyboardActionRequest.PressAndRelease(
                  duration=duration
              ),
          )
      )
    except grpc.RpcError as e:
      raise PassportHIDClientError(
          f'Failed to send keypress to HID device {device_id}.'
      ) from e

  def send_mouse_click(
      self,
      device_id: str,
      button: hid_service_pb2.MouseActionRequest.Button,
      duration_ms: int = 100,
  ):
    """Send a mouse click event to the DUT

    Args:
      device_id: The ID of the HID device to send the move to.
      button: the mouse button to click
      duration_ms: the duration in milliseconds to click the mouse.
    Raises:
      PassportHIDClientError: If the RPC fails.
      ValueError: If the duration is not greater than 0.
    """
    if duration_ms <= 0:
      raise ValueError(f'Duration must be greater than 0, got {duration_ms}.')
    duration = duration_pb2.Duration()
    duration.FromMilliseconds(duration_ms)
    try:
      self.stub.MouseAction(
          hid_service_pb2.MouseActionRequest(
              device_id=device_id,
              press_and_release=hid_service_pb2.MouseActionRequest.PressAndRelease(
                  button=button, duration=duration
              ),
          )
      )
    except grpc.RpcError as e:
      raise PassportHIDClientError(
          f'Failed to send mouse click to HID device {device_id}.'
      ) from e

  def send_mouse_move(self, device_id: str, x: int, y: int):
    """Send a mouse move event to the DUT

    Args:
      device_id: The ID of the HID device to send the move to.
      x: The x distance to move the mouse, positive numbers move to the right,
        while negative numbers move to the left.
      y: The y distance to move the mouse, positive numbers move down and
        negative numbers move up.

    Raises:
      PassportHIDClientError: If the RPC fails.
    """
    try:
      self.stub.MouseAction(
          hid_service_pb2.MouseActionRequest(
              device_id=device_id,
              move=hid_service_pb2.MouseActionRequest.Move(x=x, y=y),
          )
      )
    except grpc.RpcError as e:
      raise PassportHIDClientError(
          f'Failed to send mouse move to HID device {device_id}.'
      ) from e

  def send_mouse_scroll(self, device_id: str, distance: int):
    """Send a mouse scroll event to the DUT

    Args:
      device_id: The ID of the HID device to send the scroll to.
      distance: The distance to scroll by, positive values scroll up and
        negative values scroll down.

    Raises:
      PassportHIDClientError: If the RPC fails.
    """
    try:
      self.stub.MouseAction(
          hid_service_pb2.MouseActionRequest(
              device_id=device_id,
              scroll=hid_service_pb2.MouseActionRequest.Scroll(
                  distance=distance
              ),
          )
      )
    except grpc.RpcError as e:
      raise PassportHIDClientError(
          f'Failed to send mouse scroll to HID device {device_id}.'
      ) from e
