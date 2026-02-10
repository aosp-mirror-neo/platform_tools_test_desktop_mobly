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

"""Unit tests for dumpsys_surfaceflinger_parser."""

import os
import sys
import unittest
from unittest import mock
from lib.pasit.android import android_display_id
from lib.pasit.android import dumpsys_surfaceflinger_parser
from lib.pasit.base import base_pasit_display

DisplayId = android_display_id.AndroidDisplayId
DisplayResolution = base_pasit_display.BasePasitDisplay.DisplayResolution
TESTDATA_PATH = os.path.join(
    os.path.dirname(os.path.abspath(sys.argv[0])),
    'android',
    'testdata',
)


class DumpsysSurfaceFlingerParserTest(unittest.TestCase):
  _INTERNAL_DISPLAY_ID = DisplayId(
      display_id='0', unique_id='4613568013223667456'
  )
  _EXTERNAL_DISPLAY_ID = DisplayId(
      display_id='6', unique_id='4616379764323906308'
  )
  _NEGATIVE_UNIQUE_ID_DISPLAY_ID = DisplayId(
      display_id='0', unique_id='-5113623805080084878'
  )
  _INTERNAL_DISPLAY_RESOLUTION = DisplayResolution(width=1920, height=1200)
  _EXTERNAL_DISPLAY_RESOLUTION = DisplayResolution(width=1920, height=1080)

  def setUp(self):
    self.internal_display_lines = self._get_test_data(
        'dumpsys_surfaceflinger_internal.txt'
    ).splitlines()
    self.external_display_lines = self._get_test_data(
        'dumpsys_surfaceflinger_external.txt'
    ).splitlines()
    self.negative_unique_id_display_lines = self._get_test_data(
        'dumpsys_surfaceflinger_negative_id.txt'
    ).splitlines()

  def test_get_display_resolution_internal_display(self):
    self.parser = self._get_parser(self.internal_display_lines)
    self.assertEqual(
        self.parser.get_display_resolution(self._INTERNAL_DISPLAY_ID),
        ('0', self._INTERNAL_DISPLAY_RESOLUTION),
    )

  def test_get_display_resolution_external_display(self):
    self.parser = self._get_parser(self.external_display_lines)
    self.assertEqual(
        self.parser.get_display_resolution(self._EXTERNAL_DISPLAY_ID),
        ('0', self._EXTERNAL_DISPLAY_RESOLUTION),
    )

  def test_get_display_resolution_negative_unique_id_display(self):
    self.parser = self._get_parser(self.negative_unique_id_display_lines)
    self.assertEqual(
        self.parser.get_display_resolution(self._NEGATIVE_UNIQUE_ID_DISPLAY_ID),
        ('0', self._EXTERNAL_DISPLAY_RESOLUTION),
    )

  def test_get_supported_display_resolutions_internal_display(self):
    self.parser = self._get_parser(self.internal_display_lines)
    self.assertEqual(
        self.parser.get_supported_display_resolutions(
            self._INTERNAL_DISPLAY_ID
        ),
        {
            '0': self._INTERNAL_DISPLAY_RESOLUTION,
            '1': self._INTERNAL_DISPLAY_RESOLUTION,
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
                ('0', 1920, 1080),
                ('1', 1600, 900),
                ('2', 1280, 1024),
                ('3', 1280, 1024),
                ('4', 1152, 864),
                ('5', 1024, 768),
                ('6', 1024, 768),
                ('7', 800, 600),
                ('8', 800, 600),
                ('9', 640, 480),
                ('10', 640, 480),
                ('11', 720, 400),
            ]
        },
    )

  def _get_parser(self, display_lines):
    controller = mock.MagicMock()
    controller.adb.shell.return_value = '\n'.join(display_lines).encode('utf-8')
    return dumpsys_surfaceflinger_parser.DumpsysSurfaceFlingerParser(controller)

  def _get_test_data(self, file_name):
    file_path = os.path.join(TESTDATA_PATH, file_name)
    with open(file_path, 'r') as f:
      return f.read()


if __name__ == '__main__':
  unittest.main()
