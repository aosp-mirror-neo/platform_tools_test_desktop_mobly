"""Client for the Passport API handling the Camera Service functionality."""

import grpc

from chromiumos.test.lab.api.passport import camera_service_pb2
from chromiumos.test.lab.api.passport import camera_service_pb2_grpc


class PassportCameraBaseError(Exception):
  """Base error class for PassportCameraServiceClient."""


class PassportCameraClientError(PassportCameraBaseError):
  """Camera service RPC error for non-state-modifying requests."""


class PassportCameraServiceClient:
  """Client for the Passport API handling the Camera Service functionality."""

  def __init__(self, server_address: str):
    """Initializes the PassportCameraServiceClient.

    Args:
      server_address: The address of the Passport API server, e.g.
        'localhost:8300'.
    """

    # instantiate the channel
    self.channel = grpc.insecure_channel(server_address)

    # bind the client and the server
    self.stub = camera_service_pb2_grpc.CameraServiceStub(self.channel)

  def close(self):
    """Closes the PassportCameraServiceClient."""
    self.channel.close()

  def get_cameras(self) -> camera_service_pb2.GetCamerasResponse:
    """Gets the cameras connected to the host.

    Returns:
      The GetCamerasResponse from the Passport server with the list of attached
      cameras.
    Raises:
      PassportCameraClientError: If the RPC fails.
    """
    try:
      return self.stub.GetCameras(camera_service_pb2.GetCamerasRequest())
    except grpc.RpcError as e:
      raise PassportCameraClientError(
          'Failed to get cameras from Passport.'
      ) from e

  def get_average_pixel(
      self, camera_id: str
  ) -> camera_service_pb2.GetAveragePixelResponse:
    """Gets the average pixel color detected by the specified camera.

    Args:
      camera_id: The unique ID of the camera to capture an image and
        GetAveragePixel.
    Returns:
      The GetAveragePixelResponse from the Passport server with the average
      pixel color detected by the specified camera and the frame.
    Raises:
      PassportCameraClientError: If the RPC fails.
    """
    try:
      return self.stub.GetAveragePixel(
          camera_service_pb2.GetAveragePixelRequest(device_id=camera_id)
      )
    except grpc.RpcError as e:
      raise PassportCameraClientError(
          f'Failed to get average pixel from Passport for camera {camera_id}.'
      ) from e
