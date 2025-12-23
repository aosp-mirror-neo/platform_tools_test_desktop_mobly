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
from lib.pasit import dut_state_manager
from lib.utils import functools
from mobly import test_runner
from pasit.camera import camera_base_test

@DesktopTest(
    manual=[
        'al_external_input.test_all_the_peripherals_connected_to_basic_usb_hub',
        'al_external_webcam.connect_disconnect_external_webcam',
    ]
)
@functools.generate_tests
class UnplugExternalCameraTest(camera_base_test.CameraBaseTest):
  """Test unplugging an external camera."""

  @functools.with_variants(
      off=(dut_state_manager.PowerState.OFF,),
      suspended=(dut_state_manager.PowerState.SUSPEND,),
      on=(dut_state_manager.PowerState.ON,),
  )
  def test_unplug_external_camera(
      self, state_when_unplug_camera: dut_state_manager.PowerState):
    """Test camera state after unplugging, with power state changes.

    Args:
      state_when_unplug_camera: The power state of the DUT when external camera
        is unplugged.
    """
    self.launch_camera_app()
    self.capture_screenshots('after_launch_camera_app')
    _, external_camera_devices = (
        self.connect_external_camera()
    )
    self.capture_screenshots('after_plug_in_external_camera')

    self.switch_camera()
    self.verify_camera_app_is_using_any_device(
        external_camera_devices, 'external camera'
    )
    self.capture_screenshots('after_switch_camera')

    with dut_state_manager.EnterStateAndReturnToPowerOn(
        self.dut, state_when_unplug_camera
    ):

      self.unplug_external_camera()
    self.launch_camera_app()

    current_internal_devices = self.camera.get_connected_cameras()

    self.verify_camera_app_is_using_any_device(
        current_internal_devices, 'internal camera'
    )
    self.capture_screenshots('after_unplug_external_camera')


if __name__ == '__main__':
  test_runner.main()
