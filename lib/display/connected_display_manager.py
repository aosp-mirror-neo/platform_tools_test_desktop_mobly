# Copyright 2026 Google LLC
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

"""Abstract class and implementations for managing displays."""

import abc
import logging

from chromiumos.test.lab.api import pasit_host_pb2
from display.utils import ucd_manager
from lib.pasit import pasit_device
from lib.pasit.passport import passport_host


class DisplayManager(abc.ABC):
  """Abstract base class for managing displays."""

  @abc.abstractmethod
  def ConnectDisplays(self, display_count: int) -> None:
    """Connects the specified number of displays.

    Args:
      display_count: The number of displays to connect.
    """
    pass

  @abc.abstractmethod
  def Reset(self) -> None:
    """Resets the display configuration to a default state."""
    pass

  @abc.abstractmethod
  def GetMaxDisplays(self) -> int:
    """Returns the maximum number of supported displays.

    Returns:
      An integer specifying the maximum number of concurrent displays.
    """
    pass


class VideoTesterDisplayManager(DisplayManager):
  """Display manager implementation using a hardware video tester."""

  def __init__(
      self, host: passport_host.PassportHost, dut: pasit_device.PasitDevice
  ):
    self._ucd_mgr = ucd_manager.UcdManager.connect_to_ucd(
        host.video_tester_client, dut
    )

  def ConnectDisplays(self, display_count: int) -> None:
    self._ucd_mgr.replug_displays(display_count, wait_for_active=False)

  def Reset(self) -> None:
    self._ucd_mgr.reset_ucd_displays_state_to_default()
    self._ucd_mgr.unplug_all_displays(wait_for_active=True)

  def GetMaxDisplays(self) -> int:
    """Returns the maximum number of supported displays.

    Returns:
      An integer specifying the maximum number of concurrent displays.
    """
    return self._ucd_mgr.max_supported_displays


class SwitchDisplayManager(DisplayManager):
  """Display manager implementation using Passport switches."""

  def __init__(self, host: passport_host.PassportHost):
    self._host = host

  def ConnectDisplays(self, display_count: int) -> None:
    display_ids = self._host.get_device_ids_by_type(
        pasit_host_pb2.PasitHost.Device.Type.MONITOR
    )

    if display_count > len(display_ids):
      logging.warning(
          "Requested %d displays, but only %d are available in topology.",
          display_count,
          len(display_ids),
      )

    # Activate the requested number of displays.
    for i, display_id in enumerate(display_ids):
      if i < display_count:
        self._host.activate_device_by_id(display_id)
      else:
        self._host.deactivate_device_by_id(display_id)

  def Reset(self) -> None:
    # Resetting the host unplugs all switches.
    self._host.reset()

  def GetMaxDisplays(self) -> int:
    """Returns the maximum number of supported displays.

    Returns:
      An integer specifying the maximum number of concurrent displays.
    """
    display_ids = self._host.get_device_ids_by_type(
        pasit_host_pb2.PasitHost.Device.Type.MONITOR
    )
    return len(display_ids)
