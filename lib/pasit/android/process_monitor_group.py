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

"""Manages a collection of process monitors for an Android device."""

from typing import Type

from lib.pasit.android import adb_command_monitor
from mobly.controllers import android_device


class ProcessMonitorGroup:
  """Manages a group of AdbCommandMonitor instances for an Android device.

  This class allows starting, stopping, pausing, and resuming multiple
  process monitors associated with a single AndroidDevice controller. Monitors
  are instantiated and managed based on their class type.
  """

  def __init__(self, controller: android_device.AndroidDevice):
    """Initializes the ProcessMonitorGroup.

    Args:
      controller: An AndroidDevice object used to interact with the device.
    """
    self._controller = controller
    self._process_monitors = dict()

  def start(
      self, monitor_class: Type[adb_command_monitor.AdbCommandMonitor]
  ) -> None:
    """Starts a process monitor for the given class.

    Instantiates the monitor class with the group's AndroidDevice controller
    if an instance of this class is not already being managed. Then, starts
    the monitor. If a monitor of the same class is already in the group,
    this method does nothing.

    Args:
      monitor_class: The class of the process monitor to instantiate and start.
    """
    if monitor_class not in self._process_monitors:
      monitor = monitor_class(self._controller)
      self._process_monitors[monitor_class] = monitor

    self._process_monitors[monitor_class].start()

  def stop(
      self,
      monitor_class: Type[adb_command_monitor.AdbCommandMonitor],
      host_output_path: str | None = None,
  ) -> None:
    """Stops a specific process monitor.

    If a monitor instance of the given class exists in the group, its stop()
    method is called. Otherwise, this method does nothing.

    Args:
      monitor_class: The class of the process monitor to stop.
      host_output_path: Optional path on the host machine to copy files to,
        passed to the monitor's stop() method. If None, file copying is
        typically skipped by the monitor.
    """

    if monitor_class in self._process_monitors:
      self._process_monitors[monitor_class].stop(host_output_path)

  def pause(self) -> None:
    """Stops all active process monitors in the group.

    This method iterates through all managed monitor instances and calls
    their stop() method. The monitors remain in the group and can be restarted
    using resume().
    """
    for monitor in self._process_monitors.values():
      monitor.stop()

  def resume(self) -> None:
    """Restarts all process monitors currently held in the group.

    This method iterates through all managed monitor instances and calls
    their start() method.
    """
    for monitor in self._process_monitors.values():
      monitor.start()
