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
from lib.pasit import dut_state_manager
from lib.pasit import pasit_device
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
    ],
    cujs=[
        'b/352598161',  # Use external USB webcam
        'b/352597365',  # Switch between internal and external cameras
    ],
)
@functools.generate_tests
class LaunchWithExternalCameraTest(camera_base_test.CameraBaseTest):
  """Test launching the camera app with an external camera plugged in."""

  @functools.with_variants(
      shutdown=(dut_state_manager.PowerAction.SHUTDOWN,),
      suspend=(dut_state_manager.PowerAction.SUSPEND,),
      reboot=(dut_state_manager.PowerAction.REBOOT,),
  )
  def test_launch_with_external_camera_then(
      self, action_after_plug_camera: dut_state_manager.PowerAction
  ):
    """Test launching the camera app with an external camera plugged in when DUT is in different states."""

    internal_camera_devices, external_camera_devices = (
        self.connect_external_camera()
    )
    self.launch_camera_app()
    self.capture_screenshots('camera_app_launched')
    self.verify_camera_app_is_using_any_device(
        internal_camera_devices, 'internal camera'
    )

    self.switch_camera()
    self.capture_screenshots('after_switch_to_external_camera')
    self.verify_camera_app_is_using_any_device(
        external_camera_devices, 'external camera'
    )

    self._verify_external_camera_captures_color(
        image.NamedColor.BLUE,
        'External camera preview (on the internal display) should be showing'
        ' blue color.',
        external_camera_devices,
    )

    dut_state_manager.execute_power_action(self.dut, action_after_plug_camera)

    if action_after_plug_camera == dut_state_manager.PowerAction.SUSPEND:
      asserts.assert_true(
          self.dut.wait_app_open(pasit_device.PasitDevice.UiApplication.CAMERA),
          'Camera app should remain opened after DUT is woken up from suspend.',
      )
      self.capture_screenshots('after_dut_woken_up_from_suspend')
      self.verify_camera_app_is_using_any_device(
          external_camera_devices, 'external camera'
      )
    else:
      self.launch_camera_app()
      self.capture_screenshots('after_dut_powered_on_and_camera_app_launched')
      self.verify_camera_app_is_using_any_device(
          internal_camera_devices, 'internal camera'
      )

  def _verify_external_camera_captures_color(
      self,
      color: image.NamedColor,
      message: str,
      external_camera_devices: list[str],
  ):
    """Verifies that the external camera captures the color on the display.

    Args:
      color: The color to capture.
      message: The message to use for the assertion if the verification fails.
      external_camera_devices: The list of external camera devices.
    """
    # Maximize the camera app window early so that there is no need to wait for
    # it to be maximized later when matching the color using camera mapper.
    self.camera.maximize_camera_app_window()

    # Display-testing camera, pointed at internal display.
    camera_id = self.show_color_for_external_camera_preview(color)

    self.capture_screenshots('external_camera_preview_color')
    # for some reason the camera app is switching to internal camera at this
    # point. Check if the external camera is still being used.
    self.verify_camera_app_is_using_any_device(
        external_camera_devices, 'external camera'
    )

    # Internal display has the camera app open, showing external (tested) camera
    # capturing color from an external display.
    asserts.assert_true(
        retry.retry(
            lambda: self.camera_mapper.try_match_color(
                camera_id, color, 'external_camera_preview_color'
            ),
            policy=test_policy.CameraTestPolicy.VERIFY_EXTERNAL_CAMERA_COLOR_RETRY_POLICY,
            until=lambda result: result,
        ),
        message,
    )


if __name__ == '__main__':
  test_runner.main()
