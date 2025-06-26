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
    self.dut.get_screenshots(self.log_path, 'camera_app_launched')

    self._switch_camera()
    self.dut.get_screenshots(self.log_path, 'after_switch_to_external_camera')


if __name__ == '__main__':
  test_runner.main()
