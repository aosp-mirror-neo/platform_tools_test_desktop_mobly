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

"""Unit tests for dumpsys_battery_parser."""

import os
import sys
import unittest
from unittest import mock
from lib.pasit.android import dumpsys_battery_parser

TESTDATA_PATH = os.path.join(
    os.path.dirname(os.path.abspath(sys.argv[0])),
    'android',
    'testdata',
)


class DumpsysBatteryParserTest(unittest.TestCase):

  def setUp(self):
    self.not_charging_test_data = self._get_test_data(
        'dumpsys_battery_not_charging.txt'
    )
    self.usb_charging_test_data = self._get_test_data(
        'dumpsys_battery_usb_charging.txt'
    )

  def test_is_powered_not_charging(self):
    self.parser = self._get_parser(self.not_charging_test_data)
    self.assertFalse(self.parser.is_powered())

  def test_is_powered_usb_charging(self):
    self.parser = self._get_parser(self.usb_charging_test_data)
    self.assertTrue(self.parser.is_powered())

  def _get_parser(self, test_data):
    controller = mock.MagicMock()
    controller.adb.shell.return_value = test_data.encode('utf-8')
    return dumpsys_battery_parser.DumpsysBatteryParser(controller)

  def _get_test_data(self, file_name):
    file_path = os.path.join(TESTDATA_PATH, file_name)
    with open(file_path, 'r') as f:
      return f.read()


if __name__ == '__main__':
  unittest.main()
