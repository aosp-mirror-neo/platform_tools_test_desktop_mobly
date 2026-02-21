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

"""Tests for power operations on the DUT."""

import logging
from lib.pasit import pasit_test
from lib.pasit import peripheral_connector
from lib.utils import retry
from mobly import asserts


class PasitPowerTest(pasit_test.PasitTestClass):
  """Tests for power operations on the DUT."""

  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_DOCK

  def teardown_test(self):
    super().teardown_test()
    self.dut.enable_servo_power()

  def test_dut_power_state_with_network_device_over_dock(self):
    """Tests that Servo power can be enabled and disabled with a dock connected."""
    asserts.skip_if(
        not self.dut.is_servo_configured(), 'Servo is not configured.'
    )

    test_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_NETWORK
    asserts.skip_if(
        not self.passport_host.is_device_type_present(test_device_type, None),
        f'{pasit_test.get_device_type_name(test_device_type)} not present in'
        ' topology.',
    )

    logging.info('Disabling Servo power...')
    self.dut.disable_servo_power()
    asserts.assert_false(
        self.dut.is_powered(),
        'DUT is still powered after disabling Servo power.',
    )

    logging.info(
        'Plugging in the %s device...',
        pasit_test.get_device_type_name(test_device_type),
    )
    self.passport_host.activate_device_by_type(
        test_device_type, peripheral_connector.ConnectionTag.DOCK
    )
    self._wait_for_dut_to_be_powered('plugging in the dock')

    logging.info(
        'Unplugging the %s device...',
        pasit_test.get_device_type_name(test_device_type),
    )
    self.passport_host.deactivate_device_by_type(
        test_device_type, peripheral_connector.ConnectionTag.DOCK
    )
    asserts.assert_false(
        self.dut.is_powered(), 'DUT is still powered after unplugging the dock.'
    )

    # b/476221085 - enable_servo_power should be called after disconnecting
    # dock and network device from the DUT.
    logging.info('Enabling Servo power...')
    self.dut.enable_servo_power()
    asserts.assert_true(
        self.dut.is_powered(), 'DUT is not powered after enabling Servo power.'
    )

  # TODO: b/485708996 - this test doesn't need to be a part of presubmit.
  def test_dut_charging_from_dock(self):
    """Tests that the DUT is charging from the dock."""
    asserts.skip_if(
        not self.dut.is_servo_configured(), 'Servo is not configured.'
    )

    self.dut.disable_servo_power()
    asserts.assert_false(
        self.dut.is_powered(),
        'DUT is still powered after disabling Servo power.',
    )
    logging.info('Disabled Servo power. DUT is not powered.')

    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_DOCK)
    self._wait_for_dut_to_be_powered('turning on IP power for dock')
    logging.info('Activated dock. DUT is powered.')

  # TODO: b/485708996 - this test doesn't need to be a part of presubmit.
  def test_turn_on_power_for_dock_after_pluged_in(self):
    """Tests that the DUT is charging from the dock."""
    asserts.skip_if(
        not self.dut.is_servo_configured(), 'Servo is not configured.'
    )

    self.dut.disable_servo_power()
    asserts.assert_false(
        self.dut.is_powered(),
        'DUT is still powered after disabling Servo power.',
    )
    logging.info('Disabled Servo power. DUT is not powered.')

    self.passport_host.activate_device_by_type(
        self.DEVICE_TYPE_DOCK, tag=None, set_power=False
    )
    asserts.assert_false(
        self.dut.is_powered(), 'DUT is powered after plugging in dock.'
    )
    logging.info('Plugged in dock. DUT is still not powered.')

    self.passport_host.change_power_state_for_device_by_type(
        self.DEVICE_TYPE_DOCK, True
    )
    self._wait_for_dut_to_be_powered('plugging in IP power for dock')
    logging.info('Plugged in power for dock. DUT is powered.')

    self.passport_host.change_power_state_for_device_by_type(
        self.DEVICE_TYPE_DOCK, False
    )
    asserts.assert_false(
        self.dut.is_powered(), 'DUT is powered after unplugging power.'
    )
    logging.info('Unplugged power from dock. DUT is not powered.')

  def _wait_for_dut_to_be_powered(self, action: str) -> None:
    """Waits for the DUT to be powered."""
    asserts.assert_true(
        retry.retry(
            self.dut.is_powered,
            until=lambda result: result,
            policy=retry.RetryPolicy(),
        ),
        f'DUT is not powered after {action}.',
    )
