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

"""A smoke test that validates PasitDevice functionality.

PasitDevice is a wrapper around Mobly's device controller and servo client that
allows for easier interaction with tested devices.
"""

import logging

from mobly import asserts
from mobly import base_test
from mobly import test_runner

from pasit.lib import pasit_device


class PasitDeviceTest(base_test.BaseTestClass):

  dut: pasit_device.PasitDevice

  def setup_class(self):
    self.dut = pasit_device.create(self, requires_servo=True)

  def teardown_test(self):
    if self.dut.power_on_if_offline():
      asserts.fail('DUT is offline after test.')

  def test_shell(self):
    self.dut.shell(['echo', 'Hello', 'World!'])

  def test_reboot(self):
    logging.info('Rebooting device...')
    self.dut.reboot()

  def test_power_on_off_via_servo(self):
    logging.info('Powering off device...')
    self.dut.power_off()
    logging.info('Powering on device...')
    self.dut.power_on()

  def test_suspend(self):
    logging.info('Suspending device...')
    self.dut.suspend()
    logging.info('Resuming device...')
    self.dut.power_on()


if __name__ == '__main__':
  test_runner.main()
