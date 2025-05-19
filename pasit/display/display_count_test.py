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

from mobly import asserts
from mobly import records

from pasit.lib import pasit_display
from pasit.lib import pasit_test
from pasit.lib.utils import retry


class DisplayCountTest(pasit_test.PasitTestClass):
  """Test that counts the number of displays on the DUT."""

  _EXPECTED_DISPLAY_COUNT_BEFORE_PLUG_IN = 1
  _EXPECTED_DISPLAY_COUNT_AFTER_PLUG_IN = 2

  display: pasit_display.PasitDisplay
  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_MONITOR

  def setup_class(self):
    """Handle the setup for the test.

    Create PasitDisplay for the interacting with displays.
    """
    super().setup_class()
    self.display = self.create(pasit_display)

  def test_display_count(self):
    """Test that counts the number of displays on the DUT."""
    asserts.assert_equal(
        self.display.get_display_count(),
        self._EXPECTED_DISPLAY_COUNT_BEFORE_PLUG_IN,
        'Display count is not 1 before external display plug in.',
    )
    self._capture_display_images('before_plug_in')
    self._plug_in_external_display()
    asserts.assert_equal(
        self.try_get_display_count(self._EXPECTED_DISPLAY_COUNT_AFTER_PLUG_IN),
        self._EXPECTED_DISPLAY_COUNT_AFTER_PLUG_IN,
        'Display count is not 2 after external display plug in.',
    )
    self._capture_display_images('after_plug_in')
    self._unplug_external_display()
    asserts.assert_equal(
        self.try_get_display_count(self._EXPECTED_DISPLAY_COUNT_BEFORE_PLUG_IN),
        self._EXPECTED_DISPLAY_COUNT_BEFORE_PLUG_IN,
        'Display count is not 1 after external display unplug.',
    )

  def _plug_in_external_display(self):
    """Emulate external display plug in using passport."""
    logging.info('Plugging in external display')
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_MONITOR)

  def _unplug_external_display(self):
    """Emulate external display unplug using passport."""
    logging.info('Unplugging external display')
    self.passport_host.deactivate_device_by_type(self.DEVICE_TYPE_MONITOR)

  def try_get_display_count(self, expected_count: int) -> int:
    """Retries until the display count is equal to the expected count."""
    return retry.retry(
        self.display.get_display_count,
        until=lambda count: count == expected_count,
        max_tries=10,
        delay_seconds=2,
    )

  def _capture_display_images(self, image_prefix: str):
    """Captures an image from each PASIT camera to the log directory.

    TODO: this doesn't do any association between the image and the display,
    that will be done in future improvements.

    Args:
      image_prefix: The prefix of the image name to use for the image.
    """
    cameras = self.passport_host.get_cameras()
    for camera in cameras:
      logging.debug(
          'Capturing display image for %s camera %s to directory %s',
          image_prefix,
          camera,
          self.current_test_info.output_path,
      )
      self.passport_host.capture_image(
          camera,
          self.current_test_info.output_path,
          f'passport_img_{image_prefix}_{camera}',
      )

  def on_fail(self, record: records.TestResultRecord) -> None:
    """Called on test failure."""
    self._capture_display_images('on_fail')
    super().on_fail(record)
