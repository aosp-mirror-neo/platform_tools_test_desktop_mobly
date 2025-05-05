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


class PassportSwitchBaseError(Exception):
  """Base error class for PassportSwitchServiceClient."""


class PassportSwitchError(PassportSwitchBaseError):
  """Switch service RPC error for requests that modify switch state."""

  def __init__(self, switch_id: str, state: switch_service_pb2.SwitchPortState):
    super().__init__()
    self.switch_id = switch_id
    self.state_str = switch_service_pb2.SwitchPortState.Name(state)

  def __str__(self):
    return (
        f'Failed to set switch {self.switch_id} to state {self.state_str}'
    )


class PassportSwitchClientError(PassportSwitchBaseError):
  """Switch service RPC error for non-state-modifying requests."""


class PassportSwitchServiceClient:
  """Client for the Passport API handling the Switch Service functionality."""

  def __init__(self, server_address: str):
    """Initializes the PassportSwitchServiceClient.

    Args:
      server_address: The address of the Passport API server, e.g.
        'localhost:8300'.
    """

    # instantiate the channel
    self.channel = grpc.insecure_channel(server_address)

    # bind the client and the server
    self.stub = switch_service_pb2_grpc.SwitchServiceStub(self.channel)

  def close(self):
    """Closes the PassportSwitchServiceClient."""
    self.channel.close()

  def get_switches(self) -> switch_service_pb2.GetSwitchesResponse:
    """Gets the switches connected to the host.

    Returns:
      The GetSwitchesResponse from the Passport server with the list of attached
      switches.
    Raises:
      PassportSwitchClientError: If the RPC fails.
    """
    try:
      return self.stub.GetSwitches(switch_service_pb2.GetSwitchesRequest())
    except grpc.RpcError as e:
      raise PassportSwitchClientError(
          'Failed to get switches from Passport.'
      ) from e

  def reset_all_switches(self):
    """Re-initializes all found switches and sets them to the "disabled" state.

    Raises:
      PassportSwitchClientError: If the RPC fails.
    """
    try:
      self.stub.ResetAllSwitches(switch_service_pb2.ResetAllSwitchesRequest())
    except grpc.RpcError as e:
      raise PassportSwitchClientError(
          'Failed to reset all switches from Passport.'
      ) from e

  def disable_switch(self, switch_id: str):
    """Disables the switch with the given ID.

    Args:
      switch_id: The ID of the switch to disable.

    Raises:
      PassportSwitchError: If the switch state could not be set.
    """
    self.configure_switch_port(
        switch_id, switch_service_pb2.SwitchPortState.SWITCH_PORT_DISABLED
    )

  def enable_switch(self, switch_id: str):
    """Enables the switch with the given ID.

    Args:
      switch_id: The ID of the switch to enable.

    Raises:
      PassportSwitchError: If the switch state could not be set.
    """

    self.configure_switch_port(
        switch_id, switch_service_pb2.SwitchPortState.SWITCH_PORT_ENABLED
    )

  def configure_switch_port(
      self, switch_id: str, state: switch_service_pb2.SwitchPortState
  ):
    """Configures the switch port with the given ID and state.

    Args:
      switch_id: The ID of the switch to configure.
      state: The state to set the switch to.

    Raises:
      PassportSwitchError: If the switch state could not be set.
    """

    request = switch_service_pb2.ConfigureSwitchPortRequest(
        switch_id=switch_id,
        state=state,
    )
    try:
      self.stub.ConfigureSwitchPort(request)
    except grpc.RpcError as e:
      raise PassportSwitchError(switch_id, state) from e
