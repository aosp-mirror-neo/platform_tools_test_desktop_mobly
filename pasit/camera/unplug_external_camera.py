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

from collections.abc import Iterable, MutableSequence
import logging

from mobly import asserts
from mobly import test_runner

from pasit.lib import pasit_camera
from pasit.lib import pasit_test


class UnplugExternalCameraTest(pasit_test.PasitTestClass):
  """Test unplugging an external camera."""

  camera: pasit_camera.PasitCamera

  def setup_class(self):
    """Handle the setup for the test."""
    super().setup_class()
    self.camera = self.create(pasit_camera)

  def teardown_test(self):
    """Handle the teardown for the test."""
    super().teardown_test()
    self.camera.close_camera_app()

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

  def _plug_in_external_camera(self):
    """Emulate external camera plug in using passport."""
    logging.info('Plugging in external camera')
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_CAMERA)

  def _unplug_external_camera(self):
    """Emulate external camera unplug using passport."""
    logging.info('Unplugging external camera')
    self.passport_host.deactivate_device_by_type(self.DEVICE_TYPE_CAMERA)

  def _get_external_camera_devices(
      self, internal_camera_devices: Iterable[str]
  ) -> MutableSequence[str]:
    """Finds the external camera devices."""
    return [
        device
        for device in self.camera.get_connected_cameras()
        if device not in internal_camera_devices
    ]

  def _is_camera_app_using_any_device(self, devices: Iterable[str]) -> bool:
    """Checks if the camera app is using any of the given devices."""
    return any(
        [self.camera.is_camera_app_using_camera(device) for device in devices]
    )


if __name__ == '__main__':
  test_runner.main()
