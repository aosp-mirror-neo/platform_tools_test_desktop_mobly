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

"""A test that exercises PASIT Display component tests."""

import logging

from lib.pasit import display_helper
from lib.pasit import display_painter
from lib.pasit import pasit_display
from lib.pasit import pasit_test
from mobly import asserts
from mobly import test_runner


class PasitDisplayTest(pasit_test.PasitTestClass):

  display: pasit_display.PasitDisplay
  painter: display_painter.DisplayPainter
  helper: display_helper.DisplayHelper
  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_MONITOR

  def setup_class(self):
    super().setup_class()
    self.display = self.create(pasit_display)
    self.painter = self.create(display_painter)

  def setup_test(self):
    """Handle the setup for the test."""
    super().setup_test()
    self.helper = display_helper.DisplayHelper(
        self.passport_host,
        self.display,
        self.painter,
        self.current_test_info.output_path,
    )

  def test_get_display_count(self):
    asserts.assert_equal(
        self.display.get_display_count(), 1, 'Display count is not 1.'
    )

  def test_get_display_ids(self):
    display_ids = self.display.get_display_ids()
    logging.info('Display IDs: %s', display_ids)
    asserts.assert_equal(len(display_ids), 1, 'Display IDs count is not 1.')

  def test_get_internal_display_resolution(self):
    display_resolution = self.display.get_display_resolution()
    logging.info(
        'Display resolution without display id: %s', display_resolution
    )

    display_id = self.helper.get_internal_display_id()
    display_resolution = self.display.get_display_resolution(display_id)
    logging.info(
        'Display resolution with display id %s: %s',
        display_id,
        display_resolution,
    )

  def test_get_external_display_resolution(self):
    internal_display_id = self.helper.get_internal_display_id()
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_MONITOR)
    external_display_id = self.helper.get_external_display_id(
        internal_display_id
    )
    display_resolution = self.display.get_display_resolution(
        external_display_id
    )
    logging.info(
        'Display resolution with display id %s: %s',
        external_display_id,
        display_resolution,
    )


if __name__ == '__main__':
  test_runner.main()
