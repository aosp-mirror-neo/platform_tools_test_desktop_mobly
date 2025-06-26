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


from lib.utils import retry
from mobly import test_runner
from pasit.camera import camera_base_test


class UnplugExternalCameraTest(camera_base_test.CameraBaseTest):
  """Test unplugging an external camera."""

  def test_unplug_external_camera(self):
    """Test unplugging an external camera.

    Switch camera in the camera app, and assert that the camera app is using the
    external camera.
    Unplug the external camera, and assert that the camera app is using the
    internal camera.
    """

    internal_camera_devices = self.camera.get_connected_cameras()
    self._launch_camera_app()
    self.dut.get_screenshots(self.log_path, 'after_launch_camera_app')

    self._plug_in_external_camera()
    external_camera_devices = retry.retry(
        lambda: self._get_external_camera_devices(internal_camera_devices),
        until=lambda result: result,
    )
    self.dut.get_screenshots(self.log_path, 'after_plug_in_external_camera')

    self._switch_camera()
    self._verify_camera_app_is_using_any_device(
        external_camera_devices, 'external camera'
    )
    self.dut.get_screenshots(self.log_path, 'after_switch_camera')

    self._unplug_external_camera()
    self._verify_camera_app_is_using_any_device(
        internal_camera_devices, 'internal camera'
    )
    self.dut.get_screenshots(self.log_path, 'after_unplug_external_camera')


if __name__ == '__main__':
  test_runner.main()
