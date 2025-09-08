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

from lib.pasit import display_helper
from lib.pasit import display_painter
from lib.pasit import pasit_camera
from lib.pasit import pasit_display
from lib.pasit import pasit_test
from lib.utils import image
from lib.utils import retry
from mobly import asserts
from mobly import signals


class CameraBaseTest(pasit_test.PasitTestClass):
  """Base test for camera tests."""

  _EXTERNAL_DISPLAY_TAG = 'DOCKLESS'

  camera: pasit_camera.PasitCamera
  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_CAMERA

  helper: display_helper.DisplayHelper
  painter: display_painter.DisplayPainter
  display: pasit_display.PasitDisplay

  def setup_class(self):
    """Handle the setup for the test."""
    super().setup_class()
    self.camera = self.create(pasit_camera)
    self.display = self.create(pasit_display)
    self.painter = self.create(display_painter)

  def setup_test(self):
    """Handle the setup for the test."""
    super().setup_test()
    self.helper = display_helper.DisplayHelper(
        self.passport_host,
        self.display,
        self.painter,
        self.current_test_info.output_path,
    )

  def teardown_test(self):
    """Handle the teardown for the test."""
    self.painter.clean_color_on_display()
    self.camera.close_camera_app()
    super().teardown_test()

  def teardown_class(self):
    """Handle the teardown for the class."""
    if hasattr(self, 'painter'):
      self.painter.cleanup()
    super().teardown_class()

  def launch_camera_app(self):
    """Launches the camera app.

    Raises:
      signals.TestError: If the camera app fails to launch.
    """
    logging.info('Launching camera app')
    if not self.camera.launch_camera_app():
      raise signals.TestError('Failed to launch camera app.')

  def switch_camera(self):
    """Switches to the front or back camera."""
    logging.info('Switching camera')
    self.camera.switch_camera()

  def switch_mode(self, mode: pasit_camera.PasitCamera.Mode):
    """Switches to the photo or video mode.

    Args:
      mode: The mode to switch to.

    Raises:
      signals.TestError: If the mode switch fails.
    """
    logging.info('Switching to %s mode', mode.name)
    if not self.camera.switch_mode(mode):
      raise signals.TestError(f'Failed to switch to {mode.name} mode')

  def plug_in_external_camera(self):
    """Plugs in external camera."""
    logging.info('Plugging in external camera')
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_CAMERA)

  def unplug_external_camera(self):
    """Unplugs external camera."""
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

  def connect_external_camera(
      self,
  ) -> (MutableSequence[str], MutableSequence[str]):
    """Connects the external camera.

    Returns:
      A tuple of the internal camera devices and the external camera devices.
    """
    internal_camera_devices = self.camera.get_connected_cameras()
    self.plug_in_external_camera()
    external_camera_devices = self._wait_for_external_camera_devices(
        internal_camera_devices
    )
    return internal_camera_devices, external_camera_devices

  def verify_camera_app_is_using_any_device(
      self, devices: Iterable[str], device_name: str
  ):
    """Verifies that the camera app is using any of the given devices.

    This function will retry until the camera app is using any of the given
    devices, using the default retry interval defined in the retry method.
    Asserts that the camera app is using any of the given devices.

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

  def show_color_for_external_camera_preview(
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

  def connect_external_display(self) -> str:
    """Connects the external display.

    Returns:
      The external display id.
    """
    internal_display_id = self.helper.get_internal_display_id()
    return self._plug_in_external_display(internal_display_id)

  def _plug_in_external_display(
      self, internal_display_id: pasit_display.PasitDisplay.DisplayId
  ) -> pasit_display.PasitDisplay.DisplayId:
    """Plug in external display."""
    # External (tested) camera is pointed at external display.
    logging.info('Plugging in external display')
    # if there is only one external display, it will be activated by default.
    if (
        self.passport_host.get_device_count_by_type(self.DEVICE_TYPE_MONITOR)
        == 1
    ):
      self.passport_host.activate_device_by_type(self.DEVICE_TYPE_MONITOR)
    else:
      # skip test if external display path is not tagged in the topology.
      asserts.skip_if(
          not self.passport_host.is_device_type_present(
              self.DEVICE_TYPE_MONITOR, self._EXTERNAL_DISPLAY_TAG
          ),
          f'{self._EXTERNAL_DISPLAY_TAG} external display not found in'
          ' topology.',
      )
      self.passport_host.activate_device_by_type(
          self.DEVICE_TYPE_MONITOR, self._EXTERNAL_DISPLAY_TAG
      )
    external_display_ids = self.helper.get_external_display_ids(
        internal_display_id, 1
    )
    return external_display_ids[0]
