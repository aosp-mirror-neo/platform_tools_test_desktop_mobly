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

  TEST_DEVICE_TYPE = pasit_test.PasitTestClass.DEVICE_TYPE_NETWORK
  requires_device_type = TEST_DEVICE_TYPE

  def teardown_test(self):
    super().teardown_test()
    self.dut.enable_servo_power()

  def test_enable_disable_servo_power_with_dock(self):
    """Tests that Servo power can be enabled and disabled with a dock connected."""
    logging.info('Disabling Servo power...')
    self.dut.disable_servo_power()
    asserts.assert_false(
        self.dut.is_powered(),
        'DUT is still powered after disabling Servo power.',
    )

    logging.info(
        'Plugging in the %s device...',
        pasit_test.get_device_type_name(self.TEST_DEVICE_TYPE),
    )
    self.passport_host.activate_device_by_type(
        self.TEST_DEVICE_TYPE, peripheral_connector.ConnectionTag.DOCK
    )
    asserts.assert_true(
        retry.retry(
            self.dut.is_powered,
            until=lambda result: result,
            policy=retry.RetryPolicy(),
        ),
        'DUT is not powered after plugging in the dock.',
    )

    logging.info(
        'Unplugging the %s device...',
        pasit_test.get_device_type_name(self.TEST_DEVICE_TYPE),
    )
    self.passport_host.deactivate_device_by_type(
        self.TEST_DEVICE_TYPE, peripheral_connector.ConnectionTag.DOCK
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
