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

"""Passport USB service client."""

import grpc

from chromiumos.test.lab.api.passport import usb_tester_service_pb2
from chromiumos.test.lab.api.passport import usb_tester_service_pb2_grpc


class PassportUsbServiceClient:
  """Passport USB service client."""

  def __init__(self, server_address: str):
    self._channel = grpc.insecure_channel(server_address)
    self._stub = usb_tester_service_pb2_grpc.UsbTesterServiceStub(self._channel)
    self._tester_serial = None

  def get_usb_testers(self) -> usb_tester_service_pb2.GetTestersReply:
    """Gets the USB testers connected to the host."""
    return self._stub.GetTesters(usb_tester_service_pb2.GetTestersRequest())

  def open_usb_tester(self, tester_serial: str) -> None:
    """Opens the USB tester with the given ID.

    If the request fails all other requests will fail as well. If the serial is
    already opened the request will fail. At the end of each test the tester
    should be closed with a call to `close_usb_tester`. If the request fails
    a gRPC exception will be raised.

    Args:
      tester_serial: The serial of the USB tester to open.
    """

    ret = self._stub.OpenTester(
        usb_tester_service_pb2.OpenTesterRequest(id=tester_serial)
    )
    self._validate_reply(ret)
    self._tester_serial = tester_serial

  def close_usb_tester(self) -> None:
    """Closes the USB tester with the given ID.

    This function will use the serial which was stored as a result of opening
    the tester with `open_usb_tester`. If the tester is not open the request
    will fail with a gRPC exception.
    """
    ret = self._stub.CloseTester(
        usb_tester_service_pb2.CloseTesterRequest(id=self._tester_serial)
    )
    self._validate_reply(ret)
    self._tester_serial = None

  def get_usb_tester_active_port(
      self,
  ) -> int:
    """Gets the active port of the USB tester with the given ID."""
    ret = self._stub.GetActivePort(
        usb_tester_service_pb2.GetActivePortRequest(id=self._tester_serial)
    )
    self._validate_reply(ret)
    return ret.port_id

  def set_usb_tester_active_port(self, port_id: int) -> None:
    """Sets the active port of the USB tester with the given ID."""
    ret = self._stub.SetActivePort(
        usb_tester_service_pb2.SetActivePortRequest(
            id=self._tester_serial, port_id=port_id
        )
    )
    self._validate_reply(ret)

  def hard_reset_usb_tester(
      self,
  ) -> None:
    """Hard resets the USB tester with the given ID."""
    ret = self._stub.HardResetTester(
        usb_tester_service_pb2.HardResetTesterRequest(id=self._tester_serial)
    )
    self._validate_reply(ret)

  def replug_usb_tester(
      self,
  ) -> None:
    """Replugs the USB tester with the given ID."""
    ret = self._stub.ReplugCable(
        usb_tester_service_pb2.DoCableReplugRequest(id=self._tester_serial)
    )
    self._validate_reply(ret)

  def load_edid_usb_tester(
      self,
      edid: bytes,
  ) -> None:
    """Loads the EDID binary data to the USB tester with the given ID."""
    ret = self._stub.LoadEdid(
        usb_tester_service_pb2.LoadEdidRequest(
            id=self._tester_serial, edid=edid
        )
    )
    self._validate_reply(ret)

  def set_capability_usb_tester(
      self,
      req: usb_tester_service_pb2.SetUsbTesterCapabilityRequest,
  ) -> usb_tester_service_pb2.SetUsbTesterCapabilityReply:
    """Sets the capability of the USB tester with the given ID."""
    req.id = self._tester_serial
    ret = self._stub.SetTesterCapability(req)
    self._validate_reply(ret)
    return ret

  def get_capability_usb_tester(
      self, capability: usb_tester_service_pb2.Capability
  ) -> usb_tester_service_pb2.GetUsbTesterCapabilityReply:
    """Gets the capability of the USB tester with the given ID."""
    ret = self._stub.GetTesterCapability(
        usb_tester_service_pb2.GetUsbTesterCapabilityRequest(
            id=self._tester_serial, capability=capability
        )
    )
    self._validate_reply(ret)
    return ret

  def set_power_role_to_snk(self) -> None:
    """Sets the power role of the USB tester with the given ID."""
    self.set_capability_usb_tester(
        usb_tester_service_pb2.SetUsbTesterCapabilityRequest(
            id=self._tester_serial,
            capability=usb_tester_service_pb2.POWER_ROLE,
            power_role=usb_tester_service_pb2.SNK,
        )
    )

  def set_power_role_to_src(self) -> None:
    """Sets the power role of the USB tester with the given ID."""
    self.set_capability_usb_tester(
        usb_tester_service_pb2.SetUsbTesterCapabilityRequest(
            id=self._tester_serial,
            capability=usb_tester_service_pb2.POWER_ROLE,
            power_role=usb_tester_service_pb2.SRC,
        )
    )

  def get_power_role(self) -> usb_tester_service_pb2.PowerRole:
    """Gets the power role of the USB tester with the given ID."""
    ret = self.get_capability_usb_tester(
        usb_tester_service_pb2.Capability.POWER_ROLE
    )
    return ret.power_role

  def is_open(self) -> bool:
    """Returns True if the USB tester is open, False otherwise."""
    return self._tester_serial is not None

  def _validate_reply(
      self,
      reply: (
          usb_tester_service_pb2.SetUsbTesterCapabilityReply
          | usb_tester_service_pb2.GetUsbTesterCapabilityReply
          | usb_tester_service_pb2.OpenTesterReply
          | usb_tester_service_pb2.CloseTesterReply
          | usb_tester_service_pb2.GetActivePortReply
          | usb_tester_service_pb2.SetActivePortReply
          | usb_tester_service_pb2.HardResetTesterReply
          | usb_tester_service_pb2.DoCableReplugReply
          | usb_tester_service_pb2.LoadEdidReply
      ),
  ) -> None:
    """Validates the reply of the USB tester with the given ID."""
    if reply.err_code != 0:
      raise RuntimeError(
          f'Request for tester {self._tester_serial} returned a reply of type'
          f' {type(reply).__name__} with error code {reply.err_code} and'
          f' errors: {reply.error_msg}'
      )
