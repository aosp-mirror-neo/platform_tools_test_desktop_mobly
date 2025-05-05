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

"""Test that counts the number of displays on the DUT."""

import logging
import time

from mobly import asserts

from pasit.lib import pasit_display
from pasit.lib import pasit_test


class DisplayCountTest(pasit_test.PasitTestClass):
  """Test that counts the number of displays on the DUT."""

  display: pasit_display.PasitDisplay

  def setup_class(self):
    """Handle the setup for the test.

    Create PasitDisplay for the interacting with displays.
    """
    super().setup_class()
    self.display = self.create(pasit_display)

  def _plug_in_external_display(self):
    """Emulate external display plug in using passport."""
    logging.info('Plugging in external display')
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_MONITOR)

  def _unplug_external_display(self):
    """Emulate external display unplug using passport."""
    logging.info('Unplugging external display')
    self.passport_host.deactivate_device_by_type(self.DEVICE_TYPE_MONITOR)

  def test_display_count(self):
    """Test that counts the number of displays on the DUT."""
    asserts.assert_equal(
        self.display.get_display_count(),
        1,
        'Display count is not 1 before external display plug in.',
    )

    self._plug_in_external_display()
    asserts.assert_equal(
        self.display.get_display_count(),
        2,
        'Display count is not 2 after external display plug in.',
    )

    self._unplug_external_display()

    # TODO: b/410841131 - Add retry logic instead of sleep.
    time.sleep(2)  # Wait for the display to be disconnected.

    asserts.assert_equal(
        self.display.get_display_count(),
        1,
        'Display count is not 1 after external display unplug.',
    )
