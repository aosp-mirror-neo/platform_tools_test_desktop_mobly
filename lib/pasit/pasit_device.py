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

"""The module for PASIT device related imports and types."""

import logging
import types
from typing import Any

from lib.pasit.android import android_pasit_device
from lib.pasit.base import base_pasit_device
from lib.pasit.base import base_user_tools
from lib.utils import servo_client
from mobly import base_test
from mobly.controllers import android_device


PasitDevice = base_pasit_device.BasePasitDevice
PasitDeviceError = base_pasit_device.PasitDeviceError
SessionStatus = base_user_tools.SessionStatus


def create_controller(
    test_class: base_test.BaseTestClass, controller_module: types.ModuleType
) -> Any:
  """Creates a controller for the given test class and controller module."""
  return test_class.register_controller(controller_module)[0]


def create_servo(
    test_class: base_test.BaseTestClass, hostname: str
) -> servo_client.ServoBase | None:
  """Creates a Servo controller for the specified host given the test config."""
  if test_class.user_params.get('servo_host') and test_class.user_params.get(
      'servo_port'
  ):
    servo_uri = f'http://{test_class.user_params["servo_host"]}:{test_class.user_params["servo_port"]}'  # pylint: disable=bad-whitespace
    logging.info('Connecting to servod directly at %s', servo_uri)
    return servo_client.ServodClient(servo_uri)
  elif test_class.user_params.get('lsnexus_' + hostname):
    servo_uri = test_class.user_params['lsnexus_' + hostname]
    logging.info('Connecting to lsnexus_%s at %s', hostname, servo_uri)
    return servo_client.LSNexusClient(servo_uri)
  else:
    logging.info('No servod param provided, skipping')
    return None


def create(test_class: base_test.BaseTestClass) -> PasitDevice:
  """Creates a PasitDevice for the given test class."""
  if 'AndroidDevice' in test_class.controller_configs:
    device = create_controller(test_class, android_device)
    hostname = device.serial.split(':')[0]
  else:
    raise ValueError(
        'No device type found for controller config:'
        f' {test_class.controller_configs}'
    )

  servo = create_servo(test_class, hostname)
  if servo:
    # PASIT always wants to USE pasit peripherals and ensure that the servo
    # usb drive is not visible to the DUT.
    servo.set_servo_usbkey_power(False)
  return android_pasit_device.AndroidPasitDevice(device, servo)
