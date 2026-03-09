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

"""Component tests for get_camera_exposure utility."""

import logging

from lib.pasit import color_capturer
from lib.pasit import display_camera_mapper
from lib.pasit import display_painter
from lib.pasit import pasit_display
from lib.pasit import pasit_test
from lib.pasit import pasit_test_config
from lib.utils import image
from mobly import asserts
from mobly import base_test


# Do not schedule this test class for running in the lab meant for validating
# with local runs only.
class GetCameraExposureTest(pasit_test.PasitTestClass):
  """Component tests for get_camera_exposure."""

  bugreport_policy: pasit_test_config.BugReportPolicy = (
      pasit_test_config.BugReportPolicy.NONE
  )
  screen_recording_policy = pasit_test_config.ScreenRecordingPolicy.DISABLED

  display: pasit_display.PasitDisplay
  painter: display_painter.DisplayPainter
  mapper: display_camera_mapper.DisplayCameraMapper

  def setup_class(self):
    super().setup_class()
    self.display = self.create(pasit_display)
    self.painter = self.create(display_painter)
    self.mapper = display_camera_mapper.DisplayCameraMapper(
        self.passport_host, self.display, self.painter, self.log_path
    )
    internal_display_id = self.display.get_internal_display_id()
    logging.info('Internal display ID: %s', internal_display_id)
    self.camera_id = self.mapper.get_display_testing_camera_id(
        internal_display_id
    )
    logging.info('Camera ID for internal display: %s', self.camera_id)
    self.painter.show_color_on_display(
        image.NamedColor.MUTED_BLUE.value, internal_display_id
    )

  def teardown_class(self):
    if hasattr(self, 'painter'):
      self.painter.clean_color_on_display()
    super().teardown_class()

  @base_test.repeat(10)
  def test_get_camera_exposure_internal_display(self):
    """Verifies get_camera_exposure returns an exposure for MUTED_BLUE."""
    exposure = color_capturer.get_camera_exposure(
        camera_id=self.camera_id,
        passport=self.passport_host,
        log_path=self.log_path,
        camera_capture_prefix='test_muted_blue',
    )
    logging.info('Determined exposure: %d us', exposure)
    asserts.assert_true(exposure > 0, 'Exposure should be greater than 0.')
