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

"""A test that exercises PASIT Device component tests."""

import logging

from lib.pasit import pasit_device
from lib.utils import functools
from mobly import asserts
from mobly import base_test
from mobly import test_runner


@functools.generate_tests
class PasitDeviceTest(base_test.BaseTestClass):

  dut: pasit_device.PasitDevice

  def setup_class(self):
    self.dut = pasit_device.create(self)

  def teardown_test(self):
    if self.dut.power_on_if_offline():
      logging.error('DUT was offline after test.')
    if not self.dut.is_powered():
      logging.error('DUT is not powered after test, powering via servo.')
      self.dut.enable_servo_power()

  def test_shell(self):
    self.dut.shell(['echo', 'Hello', 'World!'])

  def test_reboot(self):
    logging.info('Rebooting device...')
    self.dut.reboot()

  def test_cold_reset(self):
    logging.info('Cold resetting device...')
    self.dut.cold_reset()

  def test_power_on_off_via_servo(self):
    asserts.skip_if(
        not self.dut.is_servo_configured(), 'Servo is not configured.'
    )
    logging.info('Powering off device...')
    self.dut.power_off()
    logging.info('Powering on device...')
    self.dut.power_on()

  def test_suspend(self):
    asserts.skip_if(
        not self.dut.is_servo_configured(), 'Servo is not configured.'
    )
    logging.info('Suspending device...')
    self.dut.suspend()
    logging.info('Resuming device...')
    self.dut.wakeup()

  def test_disable_enable_servo_power(self):
    asserts.skip_if(
        not self.dut.is_servo_configured(), 'Servo is not configured.'
    )

    asserts.assert_true(self.dut.is_powered(), 'Device is not powered.')
    logging.info('Disabling Servo power...')
    self.dut.disable_servo_power()

    logging.info('Checking if device is powered...')
    asserts.assert_false(self.dut.is_powered(), 'Device is still powered.')
    logging.info('Enabling Servo power...')
    self.dut.enable_servo_power()

    logging.info('Checking if device is powered...')
    asserts.assert_true(self.dut.is_powered(), 'Device is not powered.')

  def test_power_on_if_offline(self):
    asserts.skip_if(
        not self.dut.is_servo_configured(), 'Servo is not configured.'
    )
    logging.info('Powering off device...')
    self.dut.power_off()
    logging.info('Checking if device is offline...')
    asserts.assert_true(self.dut.is_device_offline(), 'Device is not offline.')
    logging.info('Powering on if offline...')
    asserts.assert_true(
        self.dut.power_on_if_offline(), 'Device was not offline.'
    )
    logging.info('Checking if device is online...')
    asserts.assert_true(self.dut.is_device_online(), 'Device is not online.')

  def test_set_lid_closed_open(self):
    asserts.skip_if(
        not self.dut.is_servo_configured(), 'Servo is not configured.'
    )
    logging.info('Setting lid closed...')
    self.dut.set_lid_closed()
    # expect device to be offline after setting lid closed
    # note, that this may change in the future
    self.dut.wait_for_device_offline()

    logging.info('Setting lid open...')
    self.dut.set_lid_open()
    # make sure device is online after setting lid open
    self.dut.wait_for_device_online()

  @functools.with_variants(
      settings=(pasit_device.PasitDevice.UiApplication.SETTINGS,),
      files=(pasit_device.PasitDevice.UiApplication.FILES,),
  )
  def test_launch_app(self, app: pasit_device.PasitDevice.UiApplication):
    logging.info('Launching app...')
    self.dut.launch_app(app)
    asserts.assert_true(self.dut.wait_app_open(app), 'App did not open.')
    logging.info('Capturing screenshots after launching app...')
    self.dut.capture_screenshots(
        self.current_test_info.output_path, f'test_launch_app_{str(app)}'
    )
    logging.info('Stopping app...')
    self.dut.stop_app(app)
    asserts.assert_true(self.dut.wait_app_close(app), 'App did not close.')


if __name__ == '__main__':
  test_runner.main()
