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

import enum
import typing

from chromiumos.test.lab.api.passport import usb_tester_service_pb2 as uts_pb
from chromiumos.test.lab.api.passport import usb_tester_service_pb2_grpc as uts_grpc
import grpc

DEFAULT_SRC_PDO_COUNT = 4


class PowerRole(enum.Enum):
  """Power role of the USB tester.

  SRC: Source device supplying power.
  SNK: Sink device receiving power.
  """

  POWER_ROLE_NOT_SET = uts_pb.POWER_ROLE_NOT_SET
  SRC = uts_pb.SRC
  SNK = uts_pb.SNK


class DataRole(enum.Enum):
  """Data role of the USB tester.

  UFP: Uplink facing port - periheral device.
  DFP: Downlink facing port - host of the connection.
  """

  DATA_ROLE_NOT_SET = uts_pb.DATA_ROLE_NOT_SET
  UFP = uts_pb.DATA_UFP
  DFP = uts_pb.DATA_DFP


class UsbChannel(enum.Enum):
  """USB channel of the USB tester."""

  USB_CHANNEL_NOT_SET = uts_pb.USB_CHANNEL_NOT_SET
  USB_2 = uts_pb.USB_2_HS
  USB_3 = uts_pb.USB_3_AND_2_HS


class InitPdState(enum.Enum):
  """Init PD state of the USB tester.

  PD_UFP: Uplink facing port - periheral device (sink).
  PD_DFP: Downlink facing port - host of the connection (source).
  PD_DRP: Device is Dual Role Port - can be both sink and source.
  """

  PD_INIT_STATE_NOT_SET = uts_pb.INIT_PD_STATE_NOT_SET
  PD_UFP = uts_pb.PD_UFP
  PD_DFP = uts_pb.PD_DFP
  PD_DRP = uts_pb.PD_DRP


class UsbPath(enum.Enum):
  """USB path of the USB tester.

  USB_PATH_INTERNAL: Use internal storage.
  USB_PATH_EXTERNAL: Use device connected to external USB port.
  """

  USB_PATH_NOT_SET = uts_pb.USB_PATH_NOT_SET
  USB_PATH_INTERNAL = uts_pb.USB_PATH_INTERNAL
  USB_PATH_EXTERNAL = uts_pb.USB_PATH_EXTERNAL


class ActiveCC(enum.Enum):
  """Active CC of the USB tester."""

  ACTIVE_CC_NOT_SET = uts_pb.ACTIVE_CC_NOT_SET
  CC1 = uts_pb.CC1
  CC2 = uts_pb.CC2


class PassportUsbServiceClient:
  """Passport USB service client."""

  def __init__(self, server_address: str):
    """Initializes the PassportUsbServiceClient.

    Args:
      server_address: The address of the gRPC server.
    """
    self._channel = grpc.insecure_channel(server_address)
    self._stub = uts_grpc.UsbTesterServiceStub(self._channel)
    self._tester_serial = None

  def get_usb_testers(self) -> uts_pb.GetTestersReply:
    """Gets the USB testers connected to the host."""
    return self._stub.GetTesters(uts_pb.GetTestersRequest())

  def open_usb_tester(self, tester_serial: str) -> None:
    """Opens the USB tester with the given ID.

    If the request fails all other requests will fail as well. If the serial is
    already opened the request will fail. At the end of each test the tester
    should be closed with a call to `close_usb_tester`. If the request fails
    a gRPC exception will be raised.

    Args:
      tester_serial: The serial of the USB tester to open.
    """

    ret = self._stub.OpenTester(uts_pb.OpenTesterRequest(id=tester_serial))
    self._validate_reply(ret)
    self._tester_serial = tester_serial

  def close_usb_tester(self) -> None:
    """Closes the USB tester with the given ID.

    This function will use the serial which was stored as a result of opening
    the tester with `open_usb_tester`. If the tester is not open the request
    will fail with a gRPC exception.
    """
    ret = self._stub.CloseTester(
        uts_pb.CloseTesterRequest(id=self._tester_serial)
    )
    self._validate_reply(ret)
    self._tester_serial = None

  @property
  def active_port(self) -> typing.Literal[0, 1] | None:
    """Gets the active port."""
    ret = self._stub.GetActivePort(
        uts_pb.GetActivePortRequest(id=self._tester_serial)
    )
    self._validate_reply(ret)
    return ret.port_id if ret.state == uts_pb.PortState.PORT_STATE_ON else None

  @active_port.setter
  def active_port(self, port_id: typing.Literal[0, 1] | None) -> None:
    """Sets the active port."""
    if port_id is None:
      req = uts_pb.SetActivePortRequest(
          id=self._tester_serial,
          port_id=0,
          state=uts_pb.PortState.PORT_STATE_OFF,
      )
      self._validate_reply(self._stub.SetActivePort(req))
    else:
      req = uts_pb.SetActivePortRequest(
          id=self._tester_serial,
          port_id=port_id,
          state=uts_pb.PortState.PORT_STATE_ON,
      )
      self._validate_reply(self._stub.SetActivePort(req))

  def hard_reset(self) -> None:
    """Hard resets the USB tester."""
    ret = self._stub.HardResetTester(
        uts_pb.HardResetTesterRequest(id=self._tester_serial)
    )
    self._validate_reply(ret)

  def replug(self) -> None:
    """Replugs the USB tester."""
    ret = self._stub.ReplugCable(
        uts_pb.DoCableReplugRequest(id=self._tester_serial)
    )
    self._validate_reply(ret)

  def load_edid(self, edid: bytes) -> None:
    """Loads the EDID binary data to the USB tester."""
    ret = self._stub.LoadEdid(
        uts_pb.LoadEdidRequest(id=self._tester_serial, edid=edid)
    )
    self._validate_reply(ret)

  def _set_capability(
      self, req: uts_pb.SetUsbTesterCapabilityRequest
  ) -> uts_pb.SetUsbTesterCapabilityReply:
    """Sets given capability of the USB tester."""
    req.id = self._tester_serial
    ret = self._stub.SetTesterCapability(req)
    self._validate_reply(ret)
    return ret

  def _get_capability(
      self, capability: uts_pb.Capability
  ) -> uts_pb.GetUsbTesterCapabilityReply:
    """Gets given capability of the USB tester."""
    ret = self._stub.GetTesterCapability(
        uts_pb.GetUsbTesterCapabilityRequest(
            id=self._tester_serial, capability=capability
        )
    )
    self._validate_reply(ret)
    return ret

  @property
  def power_role(self) -> PowerRole:
    """Gets the power role."""
    ret = self._get_capability(uts_pb.Capability.POWER_ROLE)
    return PowerRole(ret.power_role)

  @power_role.setter
  def power_role(self, power_role: PowerRole) -> None:
    """Sets the power role."""
    self._set_capability(
        uts_pb.SetUsbTesterCapabilityRequest(
            capability=uts_pb.POWER_ROLE, power_role=power_role.value
        )
    )

  @property
  def data_role(self) -> DataRole:
    """Gets the data role."""
    ret = self._get_capability(uts_pb.Capability.DATA_ROLE)
    return DataRole(ret.data_role)

  @data_role.setter
  def data_role(self, data_role: DataRole) -> None:
    """Sets the data role."""
    self._set_capability(
        uts_pb.SetUsbTesterCapabilityRequest(
            capability=uts_pb.DATA_ROLE, data_role=data_role.value
        )
    )

  @property
  def usb_channel(self) -> UsbChannel:
    """Gets the USB mode."""
    ret = self._get_capability(uts_pb.Capability.USB_CHANNEL)
    return UsbChannel(ret.usb_channel)

  @usb_channel.setter
  def usb_channel(self, usb_channel: UsbChannel) -> None:
    """Sets the USB mode."""
    self._set_capability(
        uts_pb.SetUsbTesterCapabilityRequest(
            capability=uts_pb.USB_CHANNEL,
            usb_channel=usb_channel.value,
        )
    )

  @property
  def pd_init_state(self) -> InitPdState:
    """Gets the PD init state."""
    ret = self._get_capability(uts_pb.Capability.INIT_PD_STATE)
    return InitPdState(ret.init_pd_state)

  @pd_init_state.setter
  def pd_init_state(self, pd_init_state: InitPdState) -> None:
    """Sets the PD init state."""
    self._set_capability(
        uts_pb.SetUsbTesterCapabilityRequest(
            capability=uts_pb.INIT_PD_STATE, init_pd_state=pd_init_state.value
        )
    )

  @property
  def data_swap_policy(self) -> bool:
    """Gets the PD data swap policy.

    Returns:
      True if the data swap is accepted, False if rejected.
    """
    ret = self._get_capability(capability=uts_pb.DATA_SWAP_POLICY)
    return ret.data_role_swap_policy

  @data_swap_policy.setter
  def data_swap_policy(self, enabled: bool) -> None:
    """Sets the PD data swap policy.

    Args:
      enabled: True to accept data swap, False to reject.
    """
    self._set_capability(
        uts_pb.SetUsbTesterCapabilityRequest(
            capability=uts_pb.DATA_SWAP_POLICY,
            data_role_swap_policy=enabled,
        )
    )

  @property
  def power_swap_policy(self) -> bool:
    """Gets the PD power swap policy.

    Returns:
      True if the power swap is accepted, False if rejected.
    """
    ret = self._get_capability(capability=uts_pb.POWER_SWAP_POLICY)
    return ret.power_role_swap_policy

  @power_swap_policy.setter
  def power_swap_policy(self, enabled: bool) -> None:
    """Sets the PD power swap policy.

    Args:
      enabled: True to accept power swap, False to reject.
    """
    self._set_capability(
        uts_pb.SetUsbTesterCapabilityRequest(
            capability=uts_pb.POWER_SWAP_POLICY,
            power_role_swap_policy=enabled,
        )
    )

  @property
  def vconn_swap_policy(self) -> bool:
    """Gets the PD VCONN swap policy.

    Returns:
      True if the vconn swap is accepted, False if rejected.
    """
    ret = self._get_capability(capability=uts_pb.VCONN_SWAP_POLICY)
    return ret.vconn_swap_policy

  @vconn_swap_policy.setter
  def set_pd_vconn_swap_policy(self, enabled: bool) -> None:
    """Sets the PD VCONN swap policy.

    Args:
      enabled: True to accept vconn swap, False to reject.
    """
    self._set_capability(
        uts_pb.SetUsbTesterCapabilityRequest(
            capability=uts_pb.VCONN_SWAP_POLICY,
            vconn_swap_policy=enabled,
        )
    )

  @property
  def dpam_enabled(self) -> bool:
    """Gets the Display Port alternate mode on/off state.

    Returns:
      True if the mode is enabled, False otherwise.
    """
    ret = self._get_capability(capability=uts_pb.DISPLAY_PORT_AM)
    return ret.display_port_am

  @dpam_enabled.setter
  def dpam_enabled(self, enabled: bool) -> None:
    """Enable or disable Display Port alternate mode.

    Args:
      enabled: True to enable the mode, False to disable.
    """
    self._set_capability(
        uts_pb.SetUsbTesterCapabilityRequest(
            capability=uts_pb.DISPLAY_PORT_AM,
            display_port_am=enabled,
        )
    )

  @property
  def usb_path(self) -> UsbPath:
    """Gets the USB path that the tester is connected to.

    External USB path is connected to external USB device,
    internal USB path is connected to the tester's internal storage.
    """
    ret = self._get_capability(capability=uts_pb.USB_PATH)
    return UsbPath(ret.usb_path)

  @usb_path.setter
  def usb_path(self, usb_path: UsbPath) -> None:
    """Sets the USB path that the tester is connected to."""
    self._set_capability(
        uts_pb.SetUsbTesterCapabilityRequest(
            capability=uts_pb.USB_PATH, usb_path=usb_path.value
        )
    )

  @property
  def active_cc(self) -> ActiveCC:
    ret = self._get_capability(capability=uts_pb.ACTIVE_CC)
    return ActiveCC(ret.active_cc)

  @active_cc.setter
  def active_cc(self, active_cc: ActiveCC) -> None:
    self._set_capability(
        uts_pb.SetUsbTesterCapabilityRequest(
            capability=uts_pb.ACTIVE_CC,
            active_cc=active_cc.value,
        )
    )

  @property
  def source_pdo_count(self) -> int:
    ret = self._get_capability(capability=uts_pb.SRC_PDO_COUNT)
    return ret.non_descrete

  @source_pdo_count.setter
  def source_pdo_count(self, count: int) -> None:
    self._set_capability(
        uts_pb.SetUsbTesterCapabilityRequest(
            capability=uts_pb.SRC_PDO_COUNT, non_descrete=count
        )
    )

  @property
  def vbus_voltage(self) -> int:
    ret = self._get_capability(capability=uts_pb.VBUS_VOLTAGE)
    return ret.non_descrete

  @property
  def vbus_current(self) -> int:
    ret = self._get_capability(capability=uts_pb.VBUS_CURRENT)
    return ret.non_descrete

  def get_dut_pdos(self) -> list[int]:
    """Gets the PD source power data objects (PDOs) of the USB tester.

    Returns:
      A list of integers representing the source PDOs.
    """
    ret = self._stub.GetPdos(
        uts_pb.GetPdosRequest(
            id=self._tester_serial,
        )
    )
    self._validate_reply(ret)
    return ret.src_pdos

  def is_open(self) -> bool:
    """Returns True if the USB tester is open, False otherwise."""
    return self._tester_serial is not None

  def pd_reset(self, soft: bool) -> None:
    """Sends a soft or hard reset command to the DUT."""
    ret = self._stub.ResetPd(
        uts_pb.ResetPdRequest(id=self._tester_serial, soft=soft)
    )
    self._validate_reply(ret)

  def simulate_key_press(self):
    """Simulates a key press on the USB tester."""
    ret = self._stub.SimulateKeyPress(
        uts_pb.SimulateKeyPressRequest(id=self._tester_serial)
    )
    self._validate_reply(ret)

  def _validate_reply(
      self,
      reply: (
          uts_pb.SetUsbTesterCapabilityReply
          | uts_pb.GetUsbTesterCapabilityReply
          | uts_pb.OpenTesterReply
          | uts_pb.CloseTesterReply
          | uts_pb.GetActivePortReply
          | uts_pb.SetActivePortReply
          | uts_pb.HardResetTesterReply
          | uts_pb.ResetPdReply
          | uts_pb.DoCableReplugReply
          | uts_pb.LoadEdidReply
          | uts_pb.GetPdosReply
          | uts_pb.SimulateKeyPressReply
      ),
  ) -> None:
    """Validates the reply from a gRPC call.

    Args:
      reply: The reply object from a gRPC call.

    Raises:
      RuntimeError: If the reply contains an error code indicating a failed
      request.
    """
    if reply.err_code != 0:
      raise RuntimeError(
          f'Request for tester {self._tester_serial} returned a reply of type'
          f' {type(reply).__name__} with error code {reply.err_code} and'
          f' errors: {reply.error_msg}'
      )
