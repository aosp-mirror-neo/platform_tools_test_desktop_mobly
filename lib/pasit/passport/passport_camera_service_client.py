"""Client for the Passport API handling the Camera Service functionality."""

from chromiumos.test.lab.api.passport import camera_service_pb2
from chromiumos.test.lab.api.passport import camera_service_pb2_grpc
import grpc
from lib.utils import image


class PassportCameraBaseError(Exception):
  """Base error class for PassportCameraServiceClient."""


class PassportCameraClientError(PassportCameraBaseError):
  """Camera service RPC error for non-state-modifying requests."""


def _hsv_to_proto(hsv: image.HSV) -> camera_service_pb2.HSV:
  """Converts an HSV object to a proto HSV object.

  Args:
    hsv: The HSV object to convert.
  Returns:
    The proto HSV object.
  """
  return camera_service_pb2.HSV(
      hue=hsv.hue,
      saturation=hsv.saturation,
      value=hsv.value
  )


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

  def analyze_hsv(
      self, camera_id: str, masks:dict[str, image.HSVMask]
  ) -> camera_service_pb2.AnalyzeHSVResponse:
    """Performs HSV analysis on the specified camera.

    Args:
      camera_id: The unique ID of the camera to perform HSV analysis on.
      masks: A dictionary of mask names to HSVMasks to compare against.
    Returns:
      The AnalyzeHSVResponse from the Passport server with the HSV analysis
      results for each mask.
    Raises:
      PassportCameraClientError: If the RPC fails.
    """
    request_masks = {}
    for name, mask in masks.items():
      request_masks[name] = camera_service_pb2.HSVMask(
          min=_hsv_to_proto(mask.min),
          max=_hsv_to_proto(mask.max),
      )
    try:
      request = camera_service_pb2.AnalyzeHSVRequest(
          device_id=camera_id,
          masks=request_masks,
      )
      return self.stub.AnalyzeImageHSV(request)
    except grpc.RpcError as e:
      raise PassportCameraClientError(
          f'Failed to analyze HSV for camera {camera_id}.'
      ) from e
