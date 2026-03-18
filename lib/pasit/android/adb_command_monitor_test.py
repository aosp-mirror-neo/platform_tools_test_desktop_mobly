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

import unittest
from unittest import mock

from lib.pasit.android import adb_command_monitor
from lib.utils import process_monitor
from mobly.controllers import android_device
from mobly.controllers.android_device import adb


class TestAdbCommandMonitor(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self.mock_controller = mock.MagicMock(spec=android_device.AndroidDevice)
    self.mock_adb = mock.MagicMock(spec=adb.AdbProxy)
    self.mock_controller.adb = self.mock_adb
    self.mock_adb_shell = mock.MagicMock()
    self.mock_adb.shell = self.mock_adb_shell
    self.mock_adb_pull = mock.MagicMock()
    self.mock_adb.pull = self.mock_adb_pull

    self.process_name = 'TestAdbProcess'
    self.command = ['my_adb_shell_command', '--arg']
    self.device_output_path = '/data/local/tmp/my_output'
    self.host_output_path = '/tmp/host_output'

    # Patch the superclass's methods to check calls
    self.mock_super_start = self.enterContext(
        mock.patch.object(
            process_monitor.ProcessMonitor, 'start', autospec=True
        )
    )
    self.mock_super_stop = self.enterContext(
        mock.patch.object(process_monitor.ProcessMonitor, 'stop', autospec=True)
    )

    self.monitor = adb_command_monitor.AdbCommandMonitor(
        command=lambda: self.command,
        process_name=self.process_name,
        controller=self.mock_controller,
        output_path=self.device_output_path,
    )
    self.mock_is_ready = self.enterContext(
        mock.patch.object(self.monitor, '_is_device_ready', autospec=True)
    )
    self.mock_is_ready.return_value = True

  def test_start_success(self):
    self.monitor.start()
    self.mock_super_start.assert_called_once()

  def test_stop_no_output_path(self):
    self.monitor.stop(host_output_path=None)
    self.mock_super_stop.assert_called_once()

  def test_stop_with_output_path(self):
    file_list = ['file1.txt', 'file2.log']
    self.mock_adb.shell.return_value = '\n'.join(file_list).encode('utf-8')

    self.monitor.stop(host_output_path=self.host_output_path)

    self.mock_super_stop.assert_called_once()
    self.mock_is_ready.assert_called_once()
    self.assertEqual(self.mock_adb.shell.call_count, 3)
    self.mock_adb.shell.assert_has_calls(
        [
            mock.call(['ls', self.device_output_path]),
            mock.call(['rm', '-f', f'{self.device_output_path}/file1.txt']),
            mock.call(['rm', '-f', f'{self.device_output_path}/file2.log']),
        ],
        any_order=True,
    )
    self.assertEqual(self.mock_adb.pull.call_count, 2)
    self.mock_adb.pull.assert_has_calls(
        [
            mock.call(
                [f'{self.device_output_path}/file1.txt', self.host_output_path]
            ),
            mock.call(
                [f'{self.device_output_path}/file2.log', self.host_output_path]
            ),
        ],
        any_order=True,
    )

  def test_stop_no_files_found(self):
    self.mock_adb.shell.return_value = b''

    self.monitor.stop(host_output_path=self.host_output_path)

    self.mock_super_stop.assert_called_once()
    self.mock_is_ready.assert_called_once()
    self.mock_adb.shell.assert_called_once_with(['ls', self.device_output_path])
    self.mock_adb.pull.assert_not_called()

  def test_stop_device_not_ready(self):
    self.mock_is_ready.return_value = False

    self.monitor.stop(host_output_path=self.host_output_path)

    self.mock_super_stop.assert_called_once()
    self.mock_is_ready.assert_called_once()
    self.mock_adb.shell.assert_not_called()


if __name__ == '__main__':
  unittest.main()
