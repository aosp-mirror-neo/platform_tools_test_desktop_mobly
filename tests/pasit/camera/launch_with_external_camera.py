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

from android.platform.test.annotations import DesktopTest
from lib.utils import image
from mobly import asserts
from mobly import test_runner
from pasit.camera import camera_base_test


@DesktopTest(
    manual=[
        'al_external_input.test_all_the_peripherals_connected_to_basic_usb_hub',
        'al_external_webcam.connect_disconnect_external_webcam',
    ]
)
class LaunchWithExternalCameraTest(camera_base_test.CameraBaseTest):
  """Test launching the camera app with an external camera plugged in."""

  def test_launch_with_external_camera(self):
    """Test launching the camera app with an external camera plugged in."""

    self.connect_external_camera()
    self.launch_camera_app()
    self.capture_screenshots('camera_app_launched')

    self.switch_camera()
    self.capture_screenshots('after_switch_to_external_camera')
    self._verify_external_camera_captures_color(
        image.NamedColor.BLUE,
        'External camera preview (on the internal display) should be showing'
        ' blue color.',
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
    camera_id = self.show_color_for_external_camera_preview(color)

    # Internal display has the camera app open, showing external (tested) camera
    # capturing color from an external display.
    self.camera.maximize_camera_app_window()
    self.capture_screenshots('external_camera_preview_color')
    asserts.assert_true(
        self.camera_mapper.try_match_color(
            camera_id, color, 'external_camera_preview_color'
        ),
        message,
    )


if __name__ == '__main__':
  test_runner.main()
