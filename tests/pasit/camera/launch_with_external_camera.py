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

"""Test launching the camera app with an external camera plugged in."""

from lib.utils import image
from lib.utils import retry
from mobly import asserts
from mobly import test_runner
from pasit.camera import camera_base_test


class LaunchWithExternalCameraTest(camera_base_test.CameraBaseTest):
  """Test launching the camera app with an external camera plugged in."""

  def test_launch_with_external_camera(self):
    """Test launching the camera app with an external camera plugged in."""

    internal_camera_devices = self.camera.get_connected_cameras()
    self._plug_in_external_camera()
    self._wait_for_external_camera_devices(internal_camera_devices)

    self._launch_camera_app()
    self._capture_screenshots('camera_app_launched')

    self._switch_camera()
    self._capture_screenshots('after_switch_to_external_camera')
    self._verify_external_camera_captures_color(
        image.NamedColor.RED,
        'External camera preview (on the internal display) should be showing'
        ' red color.',
    )

  def _verify_external_camera_captures_color(
      self, color: image.NamedColor, message: str
  ):
    """Verifies that the external camera captures the color on the display.

    Args:
      color: The color to capture.
      message: The message to use for the assertion if the verification fails.
    """
    # Display-testing camera, pointed at internal display.
    camera_id = self._show_color_for_external_camera_preview(color)

    # Internal display has the camera app open, showing external (tested) camera
    # capturing color from an external display.
    self.camera.maximize_camera_app_window()
    match_color = retry.retry(
        lambda: self.helper.capture_color(
            camera_id, 'external_camera_preview_color'
        ),
        until=lambda match_color: match_color is not None,
        max_tries=3,
        delay_seconds=1,
    )

    self._capture_screenshots('external_camera_preview_color')
    asserts.assert_is_not_none(match_color, message)
    asserts.assert_equal(match_color.value, color.value, message)


if __name__ == '__main__':
  test_runner.main()
