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

"""Test that shuts down DUT with external display plugged in."""

from lib.pasit import dut_state_manager
from lib.utils import image
from mobly import test_runner
from pasit.display import display_base_test


class ShutdownWithExternalDisplayTest(display_base_test.DisplayBaseTest):
  """Test that shuts down DUT with external display plugged in."""

  def test_shutdown_with_external_display(self):
    """Get the test name for the given test args."""
    self._skip_if_servo_needed_and_not_configured(
        dut_state_manager.PowerState.OFF
    )

    self._plug_in_external_display()
    self._verify_display_count(2, 'after external display plug in')

    with dut_state_manager.EnterStateAndReturnToPowerOn(
        self.dut, dut_state_manager.PowerState.OFF
    ):
      cameras = self.passport_host.get_cameras()
      for camera in cameras:
        self._verify_captured_color(
            camera,
            image.NamedColor.BLACK.value,
            f'black_after_shutdown_{camera}',
            'Display should be black after shutdown.',
        )
      self._unplug_external_display()

    self._verify_display_count(1, 'after external display unplug')


if __name__ == '__main__':
  test_runner.main()
