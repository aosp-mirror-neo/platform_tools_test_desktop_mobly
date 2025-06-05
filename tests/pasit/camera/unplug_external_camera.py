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

import logging

from mobly import asserts
from mobly import test_runner
from pasit.camera import camera_base_test


class UnplugExternalCameraTest(camera_base_test.CameraBaseTest):
  """Test unplugging an external camera."""

  def test_external_camera_is_not_default(self):
    """Test that the external camera is regonized by system and not used in camera app by default."""

    internal_camera_devices = self.camera.get_connected_cameras()
    logging.info('Internal camera devices: %s', internal_camera_devices)

    self._plug_in_external_camera()

    external_camera_devices = self._get_external_camera_devices(
        internal_camera_devices
    )
    logging.info('External camera devices: %s', external_camera_devices)
    asserts.assert_greater(
        len(external_camera_devices), 0, 'No external camera devices found.'
    )

    logging.info('Launching camera app')
    self.camera.launch_camera_app()

    # TODO: b/406342089 - Switch camera in the camera app, and assert that the
    # camera app is using the external camera. Unplug the external camera, and
    # assert that the camera app is using the internal camera.

    asserts.assert_false(
        self._is_camera_app_using_any_device(external_camera_devices),
        'Camera app is using external camera.',
    )

    asserts.assert_true(
        self._is_camera_app_using_any_device(internal_camera_devices),
        'Camera app is not using internal camera.',
    )


if __name__ == '__main__':
  test_runner.main()
