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

"""Unit tests for managed_process.py."""

import subprocess
import unittest
from unittest import mock

from lib.utils import managed_process


class ManagedProcessTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self.command = ['my_command', '--arg']
    self.managed_process = managed_process.ManagedProcess(
        'MyTestProcess', lambda: self.command
    )

    # Setup mock for the subprocess.Popen instance returned by
    # start_standing_subprocess
    self.mock_popen_instance = mock.MagicMock(spec=subprocess.Popen)
    self.mock_popen_instance.pid = 456
    self.mock_popen_instance.stdout = mock.MagicMock()
    self.mock_popen_instance.stderr = mock.MagicMock()
    self.mock_popen_instance.stdout.read.return_value = b'simulated stdout'
    self.mock_popen_instance.stderr.read.return_value = b'simulated stderr'
    self.mock_popen_instance.poll.return_value = None  # Simulate running

    # Patch start_standing_subprocess
    self.mock_popen = self.enterContext(
        mock.patch('mobly.utils.start_standing_subprocess', autospec=True)
    )
    self.mock_popen.return_value = self.mock_popen_instance

  def test_is_running_initially_false(self):
    self.assertFalse(self.managed_process.is_running())

  def test_start_new_process(self):
    self.managed_process.start()

    self.mock_popen.assert_called_once_with(
        self.command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    self.assertTrue(self.managed_process.is_running())

  def test_start_does_nothing_if_already_running(self):
    # First start
    self.managed_process.start()
    self.mock_popen.assert_called_once()
    self.assertTrue(self.managed_process.is_running())

    # Second start - should be no-op
    self.managed_process.start()
    self.mock_popen.assert_called_once()  # Still only called once
    self.assertTrue(self.managed_process.is_running())

  def test_start_restarts_terminated_process(self):
    # First start
    self.managed_process.start()
    self.mock_popen.assert_called_once()

    # Simulate process termination
    self.mock_popen_instance.poll.return_value = 1  # Non-zero exit code
    self.assertFalse(self.managed_process.is_running())

    # Configure mock for the second call
    self._setup_new_mock_popen_instance()

    self.managed_process.start()
    self.assertEqual(self.mock_popen.call_count, 2)
    self.assertTrue(self.managed_process.is_running())

  def test_stop_running_process(self):
    self.managed_process.start()
    self.assertTrue(self.managed_process.is_running())

    with mock.patch(
        'mobly.utils.stop_standing_subprocess', autospec=True
    ) as mock_stop:
      self.managed_process.stop()
      mock_stop.assert_called_once_with(self.mock_popen_instance)

    self.assertFalse(self.managed_process.is_running())

    self._setup_new_mock_popen_instance()

    self.managed_process.start()
    self.assertTrue(self.managed_process.is_running())

  def test_stop_noop_if_not_started(self):
    with mock.patch(
        'mobly.utils.stop_standing_subprocess', autospec=True
    ) as mock_stop:
      self.managed_process.stop()
      mock_stop.assert_not_called()

  def _setup_new_mock_popen_instance(self):
    mock_instance = mock.MagicMock(spec=subprocess.Popen)
    mock_instance.poll.return_value = None  # Simulate running
    self.mock_popen.return_value = mock_instance


if __name__ == '__main__':
  unittest.main()
