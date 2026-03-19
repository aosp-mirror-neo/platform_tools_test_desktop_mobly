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
"""Unit tests for process_monitor_group.py."""

import unittest
from unittest import mock
from lib.pasit.android import adb_command_monitor
from lib.pasit.android import process_monitor_group
from mobly.controllers import android_device


class MonitorA(adb_command_monitor.AdbCommandMonitor):
  pass


class MonitorB(adb_command_monitor.AdbCommandMonitor):
  pass


class ProcessMonitorGroupTest(unittest.TestCase):
  """Tests for the ProcessMonitorGroup class."""

  def setUp(self):
    super().setUp()
    self.mock_controller = mock.create_autospec(
        android_device.AndroidDevice, instance=True
    )
    self.group = process_monitor_group.ProcessMonitorGroup(self.mock_controller)
    # Patch the monitor classes to return mocks
    self.mock_monitor_a_inst = mock.create_autospec(MonitorA, instance=True)
    self.mock_monitor_b_inst = mock.create_autospec(MonitorB, instance=True)
    self.mock_monitor_a_cls = self.enterContext(
        mock.patch("__main__.MonitorA", return_value=self.mock_monitor_a_inst)
    )
    self.mock_monitor_b_cls = self.enterContext(
        mock.patch("__main__.MonitorB", return_value=self.mock_monitor_b_inst)
    )

  def test_start_new_monitor(self):
    """Tests starting a monitor class for the first time."""
    self.group.start(MonitorA)
    self.mock_monitor_a_cls.assert_called_once_with(self.mock_controller)
    self.mock_monitor_a_inst.start.assert_called_once()
    self.assertIn(MonitorA, self.group._process_monitors)  # pylint: disable=protected-access
    self.assertIs(
        self.group._process_monitors[MonitorA], self.mock_monitor_a_inst  # pylint: disable=protected-access
    )

  def test_start_existing_monitor(self):
    """Tests starting an already started monitor class."""
    self.group.start(MonitorA)  # First time
    self.mock_monitor_a_inst.start.reset_mock()
    self.mock_monitor_a_cls.reset_mock()
    self.group.start(MonitorA)  # Second time
    self.mock_monitor_a_cls.assert_not_called()
    self.mock_monitor_a_inst.start.assert_called_once()

  def test_stop_existing_monitor(self):
    """Tests stopping an existing monitor."""
    self.group.start(MonitorA)
    self.group.stop(MonitorA, host_output_path="/tmp/test")
    self.mock_monitor_a_inst.stop.assert_called_once_with("/tmp/test")

  def test_stop_non_existing_monitor(self):
    """Tests stopping a monitor class that hasn't been started."""
    self.group.stop(MonitorB)
    self.mock_monitor_b_inst.stop.assert_not_called()

  def test_pause_all(self):
    """Tests pause_all stops all started monitors."""
    self.group.start(MonitorA)
    self.group.start(MonitorB)
    self.group.pause_all()
    self.mock_monitor_a_inst.stop.assert_called_once()
    self.mock_monitor_b_inst.stop.assert_called_once()

  def test_pause_all_idempotent(self):
    """Tests calling pause_all multiple times."""
    self.group.start(MonitorA)
    self.group.pause_all()
    self.mock_monitor_a_inst.stop.reset_mock()
    self.group.pause_all()
    self.mock_monitor_a_inst.stop.assert_called_once()

  def test_resume_all(self):
    """Tests resume_all starts all monitors in the group."""
    self.group.start(MonitorA)
    self.group.start(MonitorB)
    self.mock_monitor_a_inst.start.reset_mock()
    self.mock_monitor_b_inst.start.reset_mock()
    self.group.resume_all()
    self.mock_monitor_a_inst.start.assert_called_once()
    self.mock_monitor_b_inst.start.assert_called_once()

  def test_resume_all_idempotent(self):
    """Tests calling resume_all multiple times."""
    self.group.start(MonitorA)
    self.group.resume_all()
    self.mock_monitor_a_inst.start.reset_mock()
    self.group.resume_all()
    self.mock_monitor_a_inst.start.assert_called_once()

  def test_lifecycle(self):
    """Tests a typical lifecycle of monitors."""
    # Start A and B
    self.group.start(MonitorA)
    self.group.start(MonitorB)
    self.assertEqual(self.mock_monitor_a_inst.start.call_count, 1)
    self.assertEqual(self.mock_monitor_b_inst.start.call_count, 1)
    # Pause all
    self.group.pause_all()
    self.mock_monitor_a_inst.stop.assert_called_once()
    self.mock_monitor_b_inst.stop.assert_called_once()
    # Resume all
    self.mock_monitor_a_inst.start.reset_mock()
    self.mock_monitor_b_inst.start.reset_mock()
    self.group.resume_all()
    self.mock_monitor_a_inst.start.assert_called_once()
    self.mock_monitor_b_inst.start.assert_called_once()
    # Stop A individually
    self.group.stop(MonitorA, "/path/1")
    self.mock_monitor_a_inst.stop.assert_called_with("/path/1")
    self.mock_monitor_a_inst.stop.reset_mock()
    self.mock_monitor_b_inst.stop.reset_mock()
    self.group.pause_all()
    self.mock_monitor_a_inst.stop.assert_called_once()
    self.mock_monitor_b_inst.stop.assert_called_once()


if __name__ == "__main__":
  unittest.main()
