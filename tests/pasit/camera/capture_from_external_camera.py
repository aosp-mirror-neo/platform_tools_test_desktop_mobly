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

"""Test recording from an external camera."""

import logging
import os
import time

from android.platform.test.annotations import DesktopTest
from lib.pasit import pasit_camera
from lib.pasit import pasit_file
from lib.pasit import test_policy
from lib.utils import functools
from lib.utils import image
from lib.utils import retry
from mobly import asserts
from mobly import test_runner
from pasit.camera import camera_base_test


@DesktopTest(
    manual=[
        'al_external_input.test_all_the_peripherals_connected_to_basic_usb_hub',
        'al_external_webcam.connect_disconnect_external_webcam',
    ]
)
@functools.generate_tests
class CaptureFromExternalCameraTest(camera_base_test.CameraBaseTest):
  """Test recording from an external camera."""

  file: pasit_file.PasitFile

  def setup_class(self):
    """Handle the setup for the test."""
    super().setup_class()
    self.file = self.create(pasit_file)
    self._cleanup_files()

  def teardown_test(self):
    """Handle the teardown for the test."""
    self._cleanup_files()
    super().teardown_test()

  @functools.with_variants(
      photo=(pasit_camera.PasitCamera.Mode.PHOTO,),
      video=(pasit_camera.PasitCamera.Mode.VIDEO,),
  )
  def test_capture_from_external_camera(
      self, camera_mode: pasit_camera.PasitCamera.Mode
  ):
    """Test recording from an external camera."""
    self.connect_external_camera()
    self.launch_camera_app()
    self.switch_camera()

    external_display_id = self.connect_external_display()
    self.switch_mode(camera_mode)
    self.capture_screenshots(f'{camera_mode.value}_mode')

    self._capture_from_external_camera(camera_mode, external_display_id)
    self._verify_captured_files_exist()
    self._copy_captured_files_to_output_path()

  def _capture_from_external_camera(
      self, mode: pasit_camera.PasitCamera.Mode, external_display_id: str
  ):
    match mode:
      case pasit_camera.PasitCamera.Mode.PHOTO:
        self._capture_photo(external_display_id)
      case pasit_camera.PasitCamera.Mode.VIDEO:
        self._capture_video(external_display_id)
      case _:
        raise ValueError(f'Unsupported camera mode: {mode}')

  def _capture_photo(self, external_display_id: str):
    self.painter.show_color_on_display(
        image.NamedColor.BLUE.value, external_display_id
    )
    logging.info('Take photo')
    self.camera.take_photo()
    self.capture_screenshots('photo_taken')

  def _capture_video(
      self, external_display_id: str, per_color_duration_seconds: int = 5
  ):
    logging.info('Start recording video')
    colors = [
        image.NamedColor.RED,
        image.NamedColor.GREEN,
        image.NamedColor.BLUE,
    ]
    self.camera.start_recording_video()
    for color in colors:
      self.painter.show_color_on_display(color.value, external_display_id)
      time.sleep(per_color_duration_seconds)  # for video content to be recorded
      self.capture_screenshots(f'{color.name}_color_recorded')
      self.painter.clean_color_on_display()
    logging.info('Stop recording video')
    self.camera.stop_recording_video()

  def _verify_captured_files_exist(self):
    file_list = retry.retry(
        lambda: self.file.list_files(self.camera.get_files_path()),
        until=lambda file_list: file_list,
        policy=test_policy.CameraTestPolicy.FIND_CAMERA_CAPTURED_FILES_RETRY_POLICY,
        exceptions=(FileNotFoundError,),
    )
    asserts.assert_greater(
        len(file_list),
        0,
        'No photos or videos were captured.',
    )

  def _copy_captured_files_to_output_path(self):
    for file in self.file.list_files(self.camera.get_files_path()):
      self.file.pull_file(file, self.current_test_info.output_path)

  def _cleanup_files(self):
    self.file.remove_file(
        os.path.join(self.camera.get_files_path(), '*'), force=True
    )


if __name__ == '__main__':
  test_runner.main()
