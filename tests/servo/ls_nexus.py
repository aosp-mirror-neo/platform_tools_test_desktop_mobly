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

"""Test basic functionality of LS Nexus with a servo and Mobly test harness."""

import logging

from lib.utils import servo_client
from mobly import asserts
from mobly import base_test
from mobly import test_runner
from mobly.controllers import android_device


class LSNexusNotConfiguredError(Exception):
  """Error when LS Nexus is not configured."""


class LSNexusTest(base_test.BaseTestClass):

  def setup_class(self):
    """Setup the test class."""
    # self.dut = self.register_controller(android_device)[0]

  def _setup_servo(self) -> servo_client.ServoBase:
    """Setup the servo."""
    # hostname = self.dut.serial.split(':')[0]
    hostname = 'localhost'
    lsnexus_uri = self.user_params.get('lsnexus_' + hostname)
    if not lsnexus_uri:
      raise LSNexusNotConfiguredError(f'no configuration found for {hostname}')
    logging.info('Connecting to LS Nexus: %s', lsnexus_uri)
    return servo_client.LSNexusClient(lsnexus_uri)

  def test_connect_to_ls_nexus(self):
    servo = None
    try:
      servo = self._setup_servo()
    except LSNexusNotConfiguredError as e:
      asserts.abort_class(f'LSNexus is not configured: {e}')
    except servo_client.ServoConnectionError as e:
      asserts.abort_class(f'Failed to connect to Servo: {e}')
    except Exception as e:
      asserts.abort_class(f'Failed to setup servo: {e}')

    asserts.assert_true(servo, 'Unexpected error, servo not configured')
    asserts.assert_true(
        isinstance(servo, servo_client.LSNexusClient),
        f'Unexpected servo type: {type(servo)}, expected LSNexusClient',
    )

  def test_get_servo_serial(self):
    """Test setting up a servo and getting the serial number."""
    servo = self._setup_servo()
    asserts.assert_true(servo, 'Unexpected error, servo not configured')
    serial = servo.get_servo_serial()
    logging.info('Servo serial number: %s', serial)
    asserts.assert_true(
        serial, 'Unexpected error, servo serial number is empty'
    )


if __name__ == '__main__':
  test_runner.main()
