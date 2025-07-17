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

"""A basic smoke test that validates communication with servod."""

from lib.pasit import pasit_device
from mobly import asserts
from mobly import base_test
from mobly import test_runner


class ServoTest(base_test.BaseTestClass):
  """Tests basic functionality of the Servo."""

  dut: pasit_device.PasitDevice

  def setup_class(self):
    self.dut = pasit_device.create(self)

  def test_servo(self):
    """Tests that the servo configured and we can communicate with it."""
    asserts.assert_true(
        self.dut.is_servo_configured(),
        'Servo is not configured, PASIT testbeds expect Servo to be'
        ' configured.',
    )
    if self.dut._servo:
      # explicitly call this for clarity of intent of the test.
      self.dut._servo.verify_connected()


if __name__ == '__main__':
  test_runner.main()
