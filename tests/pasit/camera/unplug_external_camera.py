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

"""Test unplugging an external camera."""


from android.platform.test.annotations import DesktopTest
from mobly import test_runner
from pasit.camera import camera_base_test


@DesktopTest(
    manual=[
        'al_external_input.test_all_the_peripherals_connected_to_basic_usb_hub',
        'al_external_webcam.connect_disconnect_external_webcam',
    ]
)
class UnplugExternalCameraTest(camera_base_test.CameraBaseTest):
  """Test unplugging an external camera."""

  def test_unplug_external_camera(self):
    """Test unplugging an external camera.

    Switch camera in the camera app, and assert that the camera app is using the
    external camera.
    Unplug the external camera, and assert that the camera app is using the
    internal camera.
    """

    self.launch_camera_app()
    self._capture_screenshots('after_launch_camera_app')

    internal_camera_devices, external_camera_devices = (
        self.connect_external_camera()
    )
    self._capture_screenshots('after_plug_in_external_camera')

    self.switch_camera()
    self.verify_camera_app_is_using_any_device(
        external_camera_devices, 'external camera'
    )
    self._capture_screenshots('after_switch_camera')

    self.unplug_external_camera()
    self.verify_camera_app_is_using_any_device(
        internal_camera_devices, 'internal camera'
    )
    self._capture_screenshots('after_unplug_external_camera')


if __name__ == '__main__':
  test_runner.main()
