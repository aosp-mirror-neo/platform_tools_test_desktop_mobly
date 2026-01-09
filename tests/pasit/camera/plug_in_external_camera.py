# Copyright 2026 Google LLC
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

"""Tests plugging in an external camera while the DUT is in a power state."""

from lib.pasit import dut_state_manager
from lib.utils import functools
from mobly import test_runner
from pasit.camera import camera_base_test


@functools.generate_tests
class PlugInExternalCameraTest(camera_base_test.CameraBaseTest):
  """Tests plugging in an external camera while the device is in different power states (ON, OFF, SUSPEND)."""

  @functools.with_variants(
      on=(dut_state_manager.PowerState.ON,),
      off=(dut_state_manager.PowerState.OFF,),
      suspended=(dut_state_manager.PowerState.SUSPEND,),
  )
  def test_plug_in_external_camera_when_dut(
      self, state_to_test: dut_state_manager.PowerState
  ):
    """Tests plugging in an external camera while the DUT is in a state."""

    # Get internal camera id; assuming it won't change after reboot
    internal_camera_devices = self.camera.get_connected_cameras()

    with dut_state_manager.EnterStateAndReturnToPowerOn(
        self.dut, state_to_test
    ):
      self.plug_in_external_camera()

    external_camera_devices = self._wait_for_external_camera_devices(
        internal_camera_devices
    )
    self.launch_camera_app()
    self.switch_camera()

    self.verify_camera_app_is_using_any_device(
        external_camera_devices, "external camera"
    )
    self.capture_screenshots("after_plug_in_external_camera")


if __name__ == "__main__":
  test_runner.main()
