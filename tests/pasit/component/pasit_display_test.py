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

from lib.pasit import pasit_display
from lib.pasit import pasit_test
from mobly import asserts
from mobly import test_runner


class PasitDisplayTest(pasit_test.PasitTestClass):

  display: pasit_display.PasitDisplay
  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_MONITOR

  def setup_class(self):
    super().setup_class()
    self.display = self.create(pasit_display)

  def test_get_display_count(self):
    asserts.assert_equal(
        self.display.get_display_count(), 1, 'Display count is not 1.'
    )

  def test_get_display_ids(self):
    display_ids = self.display.get_display_ids()
    logging.info('Display IDs: %s', display_ids)
    asserts.assert_equal(len(display_ids), 1, 'Display IDs count is not 1.')


if __name__ == '__main__':
  test_runner.main()
