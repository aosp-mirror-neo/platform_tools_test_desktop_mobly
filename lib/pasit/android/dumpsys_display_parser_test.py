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

"""Unit tests for dumpsys_display_parser."""

import os
import sys
import unittest
from unittest import mock
from lib.pasit.android import android_display_id
from lib.pasit.android import dumpsys_display_parser
from lib.pasit.base import base_pasit_display

DisplayId = android_display_id.AndroidDisplayId
DisplayResolution = base_pasit_display.BasePasitDisplay.DisplayResolution
TESTDATA_PATH = os.path.join(
    os.path.dirname(os.path.abspath(sys.argv[0])),
    'android',
    'testdata',
)


class DumpsysDisplayParserTest(unittest.TestCase):
  _INTERNAL_DISPLAY_ID = DisplayId(
      display_id='0', unique_id='4613568013223667456'
  )
  _EXTERNAL_DISPLAY_ID = DisplayId(
      display_id='6', unique_id='4616379764323906308'
  )
  _INTERNAL_DISPLAY_RESOLUTION = DisplayResolution(width=1920, height=1200)
  _EXTERNAL_DISPLAY_RESOLUTION = DisplayResolution(width=1920, height=1080)

  def setUp(self):
    self.internal_display_lines = self._get_test_data(
        'dumpsys_display_internal.txt'
    ).splitlines()
    self.external_display_lines = self._get_test_data(
        'dumpsys_display_external.txt'
    ).splitlines()

  def test_get_display_ids_internal_display(self):
    self.parser = self._get_parser(self.internal_display_lines)
    self.assertEqual(
        self.parser.get_display_ids(),
        [
            self._INTERNAL_DISPLAY_ID,
        ],
    )

  def test_get_display_ids_external_display(self):
    self.parser = self._get_parser(self.external_display_lines)
    self.assertEqual(
        self.parser.get_display_ids(),
        [
            self._INTERNAL_DISPLAY_ID,
            self._EXTERNAL_DISPLAY_ID,
        ],
    )

  def test_get_display_resolution_internal_display(self):
    self.parser = self._get_parser(self.internal_display_lines)
    self.assertEqual(
        self.parser.get_display_resolution(),
        self._INTERNAL_DISPLAY_RESOLUTION,
    )
    self.assertEqual(
        self.parser.get_display_resolution(self._INTERNAL_DISPLAY_ID),
        self._INTERNAL_DISPLAY_RESOLUTION,
    )

  def test_get_display_resolution_external_display(self):
    self.parser = self._get_parser(self.external_display_lines)
    self.assertEqual(
        self.parser.get_display_resolution(self._EXTERNAL_DISPLAY_ID),
        self._EXTERNAL_DISPLAY_RESOLUTION,
    )

  def test_get_supported_display_resolutions_internal_display(self):
    self.parser = self._get_parser(self.internal_display_lines)
    self.assertEqual(
        self.parser.get_supported_display_resolutions(),
        {
            '1': self._INTERNAL_DISPLAY_RESOLUTION,
            '2': self._INTERNAL_DISPLAY_RESOLUTION,
        },
    )
    self.assertEqual(
        self.parser.get_supported_display_resolutions(
            self._INTERNAL_DISPLAY_ID
        ),
        {
            '1': self._INTERNAL_DISPLAY_RESOLUTION,
            '2': self._INTERNAL_DISPLAY_RESOLUTION,
        },
    )

  def test_get_supported_display_resolutions_external_display(self):
    self.parser = self._get_parser(self.external_display_lines)
    self.assertEqual(
        self.parser.get_supported_display_resolutions(
            self._EXTERNAL_DISPLAY_ID
        ),
        {
            id: DisplayResolution(width, height)
            for id, width, height in [
                ('51', 1920, 1080),
                ('52', 1600, 900),
                ('53', 1280, 1024),
                ('54', 1280, 1024),
                ('55', 1152, 864),
                ('56', 1024, 768),
                ('57', 1024, 768),
                ('58', 800, 600),
                ('59', 800, 600),
                ('60', 640, 480),
                ('61', 640, 480),
                ('62', 720, 400),
            ]
        },
    )

  def _get_parser(self, display_lines):
    controller = mock.MagicMock()
    controller.adb.shell.return_value = '\n'.join(display_lines).encode('utf-8')
    return dumpsys_display_parser.DumpsysDisplayParser(controller)

  def _get_test_data(self, file_name):
    file_path = os.path.join(TESTDATA_PATH, file_name)
    with open(file_path, 'r') as f:
      return f.read()


if __name__ == '__main__':
  unittest.main()
