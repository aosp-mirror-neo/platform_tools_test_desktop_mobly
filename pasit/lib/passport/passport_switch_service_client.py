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

"""Client for the Passport API handling the Switch Service functionality."""

import grpc

from chromiumos.test.lab.api.passport import switch_service_pb2
from chromiumos.test.lab.api.passport import switch_service_pb2_grpc


class PassportSwitchServiceClient:
  """Client for the Passport API handling the Switch Service functionality."""

  def __init__(self, host: str, port: int):
    """Initializes the PassportSwitchServiceClient.

    Args:
      host: The host for the Passport server.
      port: The port for the Passport server.
    """

    # instantiate the channel
    self.channel = grpc.insecure_channel(f'{host}:{port}')

    # bind the client and the server
    self.stub = switch_service_pb2_grpc.SwitchServiceStub(self.channel)

  def close(self):
    """Closes the PassportSwitchServiceClient."""
    self.channel.close()

  def get_switches(self) -> switch_service_pb2.GetSwitchesResponse:
    """Gets the switches connected to the host."""

    return self.stub.GetSwitches(switch_service_pb2.GetSwitchesRequest())

  def reset_all_switches(self):
    """Re-initializes all found switches and sets them to the "disabled" state."""

    self.stub.ResetAllSwitches(switch_service_pb2.ResetAllSwitchesRequest())

  def disable_switch(self, switch_id: str):
    """Disables the switch with the given ID."""

    self.configure_switch_port(
        switch_id, switch_service_pb2.SwitchPortState.SWITCH_PORT_DISABLED
    )

  def enable_switch(self, switch_id: str):
    """Enables the switch with the given ID."""

    self.configure_switch_port(
        switch_id, switch_service_pb2.SwitchPortState.SWITCH_PORT_ENABLED
    )

  def configure_switch_port(
      self, switch_id: str, state: switch_service_pb2.SwitchPortState
  ):
    """Configures the switch port with the given ID and state."""

    request = switch_service_pb2.ConfigureSwitchPortRequest(
        switch_id=switch_id,
        state=state,
    )

    self.stub.ConfigureSwitchPort(request)
