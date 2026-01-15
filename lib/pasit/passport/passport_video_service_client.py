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

"""Passport Video service client."""

from __future__ import annotations
import logging
import time
from chromiumos.test.lab.api.passport import video_tester_service_pb2
from chromiumos.test.lab.api.passport import video_tester_service_pb2_grpc
import grpc
from lib.utils import retry


class PassportVideoServiceClient:
  """Passport Video service client."""

  def __init__(self, server_address: str):
    self._channel = grpc.insecure_channel(
        server_address,
        options=[
            ("grpc.max_send_message_length", 256 * 1024 * 1024),  # 256MB
            ("grpc.max_receive_message_length", 256 * 1024 * 1024),  # 256MB
        ],
    )
    self._stub = video_tester_service_pb2_grpc.VideoTesterServiceStub(
        self._channel
    )
    self._tester_id = None

  def _ensure_tester_open(self):
    """Raises ValueError if no tester is currently open."""
    if self._tester_id is None:
      raise ValueError(
          "No video tester is currently open. Call open_video_tester first."
      )

  def get_connected_video_testers(
      self,
  ) -> list[video_tester_service_pb2.VideoTester]:
    """Gets the video testers connected to passport.

    Returns:
        A list of connected video testers.
    """
    response = self._stub.GetVideoTesters(
        video_tester_service_pb2.GetVideoTestersRequest()
    )
    return list(response.testers)

  def open_video_tester(
      self,
      tester_id: str,
  ) -> bool:
    """Opens a video tester for interaction and stores its ID.

    Args:
        tester_id: The ID of the tester to open retrieved from
          get_connected_video_testers.

    Returns:
        True if the tester was opened successfully.
    """
    if self._tester_id is not None:
      raise ValueError(
          f"A tester ({self._tester_id}) is already open. Close it first."
      )
    response = self._stub.OpenVideoTester(
        video_tester_service_pb2.OpenVideoTesterRequest(id=tester_id)
    )
    if response.success:
      self._tester_id = tester_id
    return response.success

  def close_video_tester(
      self,
  ) -> bool:
    """Closes the currently open video tester.

    Returns:
        True if the tester was closed successfully.
    """
    self._ensure_tester_open()
    response = self._stub.CloseVideoTester(
        video_tester_service_pb2.CloseVideoTesterRequest(id=self._tester_id)
    )
    if response.success:
      self._tester_id = None
    return response.success

  def get_roles_available_at_video_tester(
      self,
  ) -> list[video_tester_service_pb2.Role]:
    """Gets the supported roles for the open video tester.

    Roles refer to the physical connection of the Video Tester and the DUT
    such as DP or USB-C.

    Returns:
      A list of supported roles for the open video tester.
    """
    self._ensure_tester_open()
    response = self._stub.GetRolesVideoTester(
        video_tester_service_pb2.GetRolesRequest(id=self._tester_id)
    )
    return list(response.roles)

  def set_role_for_video_tester(
      self,
      role: video_tester_service_pb2.Role,
  ) -> bool:
    """Sets the role for the open video tester.

    Args:
        role: The role to set.

    Returns:
        True if the role was set successfully.
    """
    self._ensure_tester_open()
    response = self._stub.SetRoleVideoTester(
        video_tester_service_pb2.SetRoleRequest(id=self._tester_id, role=role)
    )
    return response.success

  def load_edid_at_stream(
      self,
      edid: bytes,
      id_stream: int,
  ) -> bool:
    """Loads EDID data onto a stream of the open video tester.

    Args:
        edid: The EDID data bytes.
        id_stream: The stream ID to load the EDID onto.

    Returns:
        True if the EDID was loaded successfully.
    """
    self._ensure_tester_open()
    response = self._stub.LoadEdidVideoTester(
        video_tester_service_pb2.LoadEdidVideoTesterRequest(
            id=self._tester_id, edid=edid, id_stream=id_stream
        )
    )
    return response.success

  def get_stream_info_for_all_streams(
      self,
      timeout_sec: int = 20,
  ) -> list[video_tester_service_pb2.StreamInfoVideoTester]:
    """Gets the stream information for the open video tester.

    Stream info might not be available between attach states, raising an
    exception in that case, so this method waits for the stream info to be
    available or the timeout is reached.

    Args:
        timeout_sec: Maximum time to wait for stream info to be available.

    Returns:
        A list of active video stream information objects.
    """
    self._ensure_tester_open()

    def _get_stream_info():
      response = self._stub.GetStreamInfoVideoTester(
          video_tester_service_pb2.GetStreamInfoVideoTesterRequest(
              id=self._tester_id
          )
      )
      return list(response.streams)

    return retry.retry(
        _get_stream_info,
        retry.RetryPolicy(max_tries=timeout_sec, delay_seconds=0),
        exceptions=(grpc.RpcError,),
    )

  def get_screenshot_at_stream(
      self,
      id_stream: int,
  ) -> bytes:
    """Captures a screenshot from a stream of the open video tester.

    Args:
        id_stream: The stream ID to capture the screenshot from.

    Returns:
        The screenshot in bytes.
    """
    self._ensure_tester_open()
    response = self._stub.ScreenshotVideoTester(
        video_tester_service_pb2.ScreenshotVideoTesterRequest(
            id=self._tester_id, id_stream=id_stream
        )
    )
    return response.screenshot

  def set_dp_link_capabilities(
      self,
      mst: bool,
      ss_sbm: bool,
      mst_sink_count: int | None = None,
      scrambler_seed: int | None = None,
      max_lane: int | None = None,
      video_spec: video_tester_service_pb2.VideoSpecification | None = None,
      dsc: bool | None = None,
  ) -> bool:
    """Sets the DP link parameters for the open video tester.

    Args:
        mst: Multi-Stream Transport setting.
        ss_sbm: Single-Stream Stream Buffer Management setting.
        mst_sink_count: Number of MST sinks.
        scrambler_seed: Scrambler seed value.
        max_lane: Maximum lane count.
        video_spec: The video specification to apply.
        dsc: Enable or disable Display Stream Compression.

    Returns:
        True if the link parameters were set successfully.
    """
    self._ensure_tester_open()
    request = video_tester_service_pb2.SetLinkVideoTesterRequest(
        id=self._tester_id
    )
    request.mst = mst
    if ss_sbm is not None:
      request.ss_sbm = ss_sbm
    if mst_sink_count is not None:
      request.mst_sink_count = mst_sink_count
    if scrambler_seed is not None:
      request.scrambler_seed = scrambler_seed
    if max_lane is not None:
      request.max_lane = max_lane
    if video_spec is not None:
      request.video_spec.CopyFrom(video_spec)
    if dsc is not None:
      request.dsc = dsc

    try:
      self._stub.SetLinkVideoTester(request)
      time.sleep(1)
      return True
    except grpc.RpcError:
      logging.exception("Error setting link parameters")
      return False

  def get_dp_link_capabilities(
      self,
  ) -> video_tester_service_pb2.GetLinkVideoTesterResponse:
    """Gets the link parameters for the open video tester.

    Returns:
        The link parameters response proto.
    """
    self._ensure_tester_open()
    return self._stub.GetLinkVideoTester(
        video_tester_service_pb2.GetLinkVideoTesterRequest(id=self._tester_id)
    )

  def perform_attach_operation(
      self,
      attach: bool,
  ) -> bool:
    """After setting a display, attach to the DUT.

    Args:
        attach: True to simulate attach, False to simulate detach.

    Returns:
        True if the attach/detach simulation was successful.
    """
    self._ensure_tester_open()
    try:
      self._stub.AttachVideoTester(
          video_tester_service_pb2.AttachVideoTesterRequest(
              id=self._tester_id, attach=attach
          )
      )
      time.sleep(5)
      return True
    except grpc.RpcError:
      logging.exception("Error attaching/detaching display")
      return False

  def send_hpd_pulse(
      self,
      pulse_duration_ms: int | None = None,
  ) -> bool:
    """Sends an HPD pulse to the DUT.

    Args:
        pulse_duration_ms: Optional duration of the pulse in milliseconds.

    Returns:
        True if the HPD pulse was sent successfully.
    """
    self._ensure_tester_open()
    request = video_tester_service_pb2.HpdPulseVideoTesterRequest(
        id=self._tester_id
    )
    if pulse_duration_ms is not None:
      request.pulse_duration_ms = pulse_duration_ms
    try:
      self._stub.HpdPulseVideoTester(request)
      return True
    except grpc.RpcError:
      logging.exception("Error sending HPD pulse")
      return False

  def run_compliance_tests(
      self,
      tests: list[video_tester_service_pb2.ComplianceTestVideoTester],
      board: str,
      model: str,
  ) -> tuple[
      list[video_tester_service_pb2.ComplianceTestResultVideoTester], str
  ]:
    """Runs a set of compliance tests identified by their reference numbers.

    Args:
        tests: A list of ComplianceTestVideoTester objects.
        board: The board of the DUT (e.g., "brya", "fatcat").
        model: The model of the DUT (e.g., "redrix", "mithrax").

    Returns:
        A tuple containing:
          - A list of compliance test results.
          - A string containing the HTML report of the tests.
    """
    self._ensure_tester_open()
    request = video_tester_service_pb2.RunComplianceTestRequest(
        id=self._tester_id, tests=tests, platform=board, model=model
    )
    response = self._stub.RunComplianceTest(request)
    return response.results, response.results_html

  def is_open(self) -> bool:
    """Returns True if the video tester is open, False otherwise."""
    return self._tester_id is not None

  def start_event_capture(
      self,
      dprx_config: (
          video_tester_service_pb2.DpRxEventCaptureConfig | None
      ) = None,
      dptx_config: (
          video_tester_service_pb2.DpTxEventCaptureConfig | None
      ) = None,
  ) -> bool:
    """Starts event capture with the specified configuration.

    Args:
        dprx_config: Configuration for DP RX event capture.
        dptx_config: Configuration for DP TX event capture.

    Returns:
        True if event capture was started successfully.
    """
    self._ensure_tester_open()
    request = video_tester_service_pb2.StartEventCaptureRequest(
        id=self._tester_id,
        dprx_config=dprx_config,
        dptx_config=dptx_config,
    )

    try:
      self._stub.StartEventCapture(request)
      return True
    except grpc.RpcError:
      logging.exception("Error starting event capture")
      return False

  def stop_event_capture(
      self,
      generate_reports: bool = False,
  ) -> tuple[bytes | None, bytes | None]:
    """Stops event capture and optionally generates reports.

    Args:
        generate_reports: If True, generate and return capture reports.

    Returns:
        A tuple containing (dptx_capture_html, dprx_capture_html).
        Each element is bytes if report is generated, else None.
    """
    self._ensure_tester_open()
    request = video_tester_service_pb2.StopEventCaptureRequest(
        id=self._tester_id, generate_reports=generate_reports
    )
    try:
      response = self._stub.StopEventCapture(request)
      return response.dptx_capture_html, response.dprx_capture_html
    except grpc.RpcError:
      logging.exception("Error stopping event capture")
      return None, None

  def __del__(self):
    """Closes the tester (if open) and the gRPC channel."""
    if self._tester_id:
      try:
        self._stub.CloseVideoTester(
            video_tester_service_pb2.CloseVideoTesterRequest(id=self._tester_id)
        )
      except grpc.RpcError:
        logging.exception("Error closing video tester")
    if self._channel:
      self._channel.close()
