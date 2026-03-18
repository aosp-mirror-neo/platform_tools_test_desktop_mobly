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

"""Unit tests for process_monitor.py."""

import threading
import unittest
from unittest import mock

from lib.utils import managed_process
from lib.utils import process_monitor


class TestProcessMonitor(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self.process_name = 'TestProcess'
    self.command = lambda: ['test_cmd', '--arg']
    self.is_ready = mock.Mock(return_value=True)

    # Setup mock for managed_process.ManagedProcess, threading.Thread, and
    # threading.Event
    self.mock_process_instance = mock.MagicMock(
        spec=managed_process.ManagedProcess
    )
    self.mock_thread_instance = mock.MagicMock(spec=threading.Thread)
    self.mock_cancel_event_inst = mock.MagicMock(spec=threading.Event)

    # Patch managed_process.ManagedProcess, threading.Thread, and
    # threading.Event
    self.mock_process = self.enterContext(
        mock.patch('lib.utils.managed_process.ManagedProcess', autospec=True)
    )
    self.mock_process.return_value = self.mock_process_instance
    self.mock_thread = self.enterContext(
        mock.patch('threading.Thread', autospec=True)
    )
    self.mock_thread.return_value = self.mock_thread_instance
    self.mock_event = self.enterContext(
        mock.patch('threading.Event', autospec=True)
    )
    self.mock_event.return_value = self.mock_cancel_event_inst

    # Patch atexit.register
    self.mock_atexit_register = self.enterContext(
        mock.patch('atexit.register', autospec=True)
    )

    # Mock time.sleep
    self.mock_sleep = self.enterContext(mock.patch('time.sleep', autospec=True))

    self.monitor = process_monitor.ProcessMonitor(
        name=self.process_name,
        command=self.command,
        start_condition=self.is_ready,
    )

  def test_initialization(self):
    self.mock_process.assert_called_once_with(self.process_name, self.command)
    self.mock_event.assert_called_once()
    self.mock_atexit_register.assert_called_once_with(
        self.monitor._cleanup  # pylint: disable=protected-access
    )

  def test_start_creates_and_starts_thread(self):
    self.monitor.start()

    self.mock_cancel_event_inst.clear.assert_called_once()
    self.mock_thread.assert_called_once_with(
        target=self.monitor._watch,  # pylint: disable=protected-access
        args=[],
        daemon=True,
        name=f'{self.process_name}_watcher_thread',
    )
    self.mock_thread_instance.start.assert_called_once()

  def test_start_already_running(self):
    self.monitor.start()  # First start
    self.monitor.start()  # Second start

    self.mock_thread.assert_called_once_with(
        target=self.monitor._watch,  # pylint: disable=protected-access
        args=[],
        daemon=True,
        name=f'{self.process_name}_watcher_thread',
    )
    self.mock_thread_instance.start.assert_called_once()

  def test_stop_not_running(self):
    self.monitor.stop()
    self.mock_cancel_event_inst.set.assert_called_once()
    self.mock_thread_instance.join.assert_not_called()
    self.assertIsNone(self.monitor._watcher_thread)  # pylint: disable=protected-access

  def test_stop_running(self):
    self.monitor.start()
    self.monitor.stop()
    self.mock_cancel_event_inst.set.assert_called_once()
    self.mock_thread_instance.join.assert_called_once()
    self.assertIsNone(self.monitor._watcher_thread)  # pylint: disable=protected-access

  def test_watch_loop_starts_process(self):
    self.mock_cancel_event_inst.is_set.side_effect = [False, False, False, True]
    self.mock_process_instance.is_running.side_effect = [False, False, True]
    self.is_ready.return_value = True

    self.monitor._watch()  # pylint: disable=protected-access

    self.assertEqual(self.mock_process_instance.start.call_count, 2)
    self.mock_process_instance.stop.assert_called_once()

  def test_watch_loop_start_condition_not_met(self):
    self.mock_cancel_event_inst.is_set.side_effect = [False, False, True]
    self.mock_process_instance.is_running.return_value = False
    self.is_ready.return_value = False

    self.monitor._watch()  # pylint: disable=protected-access

    self.mock_process_instance.start.assert_not_called()
    self.mock_process_instance.stop.assert_called_once()

  def test_watch_loop_process_already_running(self):
    self.mock_cancel_event_inst.is_set.side_effect = [False, False, True]
    self.mock_process_instance.is_running.return_value = True
    self.is_ready.return_value = True

    self.monitor._watch()  # pylint: disable=protected-access

    self.mock_process_instance.start.assert_not_called()
    self.mock_process_instance.stop.assert_called_once()

  def test_watch_exception_handling(self):
    self.mock_cancel_event_inst.is_set.side_effect = [False, True]
    # pylint: disable=protected-access
    self.mock_process_instance._process.start.side_effect = Exception(
        'Test Exception'
    )

    self.monitor._watch()
    # pylint: enable=protected-access

    # Finally block still runs
    self.mock_process_instance.stop.assert_called_once()


if __name__ == '__main__':
  unittest.main()
