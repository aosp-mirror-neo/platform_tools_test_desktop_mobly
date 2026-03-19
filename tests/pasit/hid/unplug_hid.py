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

"""Test HID operability after unplugging and plugging in."""

import logging

from android.platform.test.annotations import DesktopTest
from lib.pasit import dut_state_manager
from lib.pasit import pasit_hid
from lib.pasit import test_policy
from lib.utils import functools
from lib.utils import retry
from mobly import asserts
from mobly import test_runner
from pasit.hid import hid_base_test


@DesktopTest(
    cujs=[
        'b/471032468',  # HID continue working after unplug and replug
    ],
)
@functools.generate_tests
class UnplugHIDTest(hid_base_test.HIDBaseTest):
  """Test HID operability after unplugging and plugging in."""

  hid: pasit_hid.PasitHID

  def setup_class(self) -> None:
    """Setup for the test class."""
    super().setup_class()
    self.hid = self.create(pasit_hid)

  def teardown_class(self) -> None:
    """Cleanup after all test cases in the class are done."""
    if hasattr(self, 'hid'):
      self.hid.cleanup()
    super().teardown_class()

  @functools.with_variants(
      on=(dut_state_manager.PowerState.ON,),
      suspended=(dut_state_manager.PowerState.SUSPEND,),
  )
  def test_unplug_hid_when_dut(
      self, state_when_unplug_hid: dut_state_manager.PowerState
  ):
    """Test HID operability after plugging in and unplugging."""

    self.skip_if_servo_needed_and_not_configured(state_when_unplug_hid)

    self.plug_in_hid_emulator_and_verify(self.hid)
    logging.info('HID plug-in successful.')

    with dut_state_manager.EnterStateAndReturnToPowerOn(
        self.dut,
        state_when_unplug_hid,
    ):
      logging.info('Unplugging HID emulator from DUT')
      self.unplug_hid_emulator()

    hid_devices = retry.retry(
        self.hid.get_hid_emulator_devices,
        until=lambda hids: len(hids) == 0,
        policy=test_policy.HIDTestPolicy.DETECT_UNPLUGGED_HID_DEVICES_RETRY_POLICY,
    )

    asserts.assert_equal(
        0,
        len(hid_devices),
        'Expected 0 HID devices after unplugging, but found:'
        f' {len(hid_devices)}',
    )
    logging.info('HID is no longer detected.')

    # Re-plug and verify functionality
    self.plug_in_hid_emulator_and_verify(self.hid)

    logging.info('Verifying Keyboard operability')
    self.validate_keyboard_input(self.hid)


if __name__ == '__main__':
  test_runner.main()
