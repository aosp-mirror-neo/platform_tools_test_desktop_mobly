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

"""Base test for camera tests."""

from collections.abc import Iterable, MutableSequence
import logging

from lib.pasit import pasit_camera
from lib.pasit import pasit_test
from lib.utils import image
from lib.utils import retry
from mobly import asserts
from mobly import signals


class CameraBaseTest(pasit_test.PasitTestClass):
  """Base test for camera tests."""

  camera: pasit_camera.PasitCamera
  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_CAMERA

  def setup_class(self):
    """Handle the setup for the test."""
    super().setup_class()
    self.camera = self.create(pasit_camera)

  def teardown_test(self):
    """Handle the teardown for the test."""
    self.camera.close_camera_app()
    super().teardown_test()

  def _launch_camera_app(self):
    """Launches the camera app.

    Raises:
      signals.TestError: If the camera app fails to launch.
    """
    logging.info('Launching camera app')
    if not self.camera.launch_camera_app():
      raise signals.TestError('Failed to launch camera app.')

  def _switch_camera(self):
    """Switches to the front or back camera."""
    logging.info('Switching camera')
    self.camera.switch_camera()

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

  def _wait_for_external_camera_devices(
      self, devices: Iterable[str]
  ) -> MutableSequence[str]:
    """Waits for the external camera devices to be detected."""
    return retry.retry(
        lambda: self._get_external_camera_devices(devices),
        until=lambda result: result,
    )

  def _verify_camera_app_is_using_any_device(
      self, devices: Iterable[str], device_name: str
  ):
    """Verifies that the camera app is using any of the given devices.

    This function will retry until the camera app is using any of the given
    devices, using the default retry interval defined in the retry method.

    Args:
      devices: The list of camera devices to check.
      device_name: The name of the device to use in the error message.
    """
    asserts.assert_true(
        retry.retry(
            lambda: self._is_camera_app_using_any_device(devices),
            until=lambda result: result,
        ),
        f'Camera app is not using any of {device_name}.',
    )

  def _show_color_for_external_camera_preview(
      self, color: image.NamedColor
  ) -> str:
    """Show the color on the external display for external camera preview.

    Plug in external display and show the color on the external display for the
    external camera to capture and show on the camera app preview on the
    internal display.

    Args:
      color: The color to show on the external display.

    Returns:
      The camera id that is pointed at the internal display.
    """
    internal_display_id = self.helper.get_internal_display_id()
    # Display-testing camera, pointed at internal display.
    camera_id = self.helper.get_display_testing_camera_id(internal_display_id)
    external_display_id = self._plug_in_external_display(internal_display_id)
    # Show color on external display to validate external camera captures it.
    self.painter.show_color_on_display(color.value, external_display_id)
    return camera_id

  def _plug_in_external_display(self, internal_display_id: str) -> str:
    """Plug in external display."""
    # External (tested) camera is pointed at external display.
    logging.info('Plugging in external display')
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_MONITOR)
    return self.helper.get_external_display_id(internal_display_id)
