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

"""Base class for UTC-274 tests that sets tester state between tests."""

import functools
import logging

from chromiumos.test.lab.api import pasit_host_pb2
from google.protobuf import json_format
from lib.mobly.typec import typec_android_device
from lib.mobly.typec import utc_params
from lib.pasit import pasit_device
from lib.pasit.passport import passport_host
from lib.pasit.passport import passport_usb_service_client as usb
from mobly import asserts
from mobly import base_test
from mobly.controllers import android_device


def test_entry(func):
  """Decorator for test entry.

  Args:
    func: The test function to decorate.

  Returns:
    The decorated test function.

  Performs common actions for all tests that are:
    - print iterations count
    - apply UTC params to the tester
  """

  @functools.wraps(func)
  def wrapper(*args, **_):
    instance = args[0]
    params = args[1]
    logging.info('Running %d iterations', params.iterations)
    params.apply(instance.utc)
    return func(instance, params)

  return wrapper


class UtcBaseTest(base_test.BaseTestClass):
  """Base class for UTC-274 tests.

  This class sets up and resets UTC-274 state between tests.
  It also provides helper methods for checking the displays state.
  """

  passport: passport_host.PassportHost
  utc: usb.PassportUsbServiceClient
  ads: list[android_device.AndroidDevice]
  dut: android_device.AndroidDevice
  enabled_ports: list[int]

  def setup_class(self):
    super().setup_class()
    self.passport = None
    self.servo = None

    # Setup the UTC-274.
    self.passport = self.register_controller(passport_host)[0]

    asserts.skip_if(
        not self.passport.get_device_ids_by_type(
            pasit_host_pb2.PasitHost.Device.Type.USB_TESTER
        ),
        'No USB tester found in the topology.',
    )

    self.utc = self.passport.usb_tester_client

    # Set the tester's initial state.
    self._set_usb_tester_default_state()

    # Register android device.
    self.ads = self.register_controller(android_device)
    self.dut = typec_android_device.TypecAndroidDevice(self.ads[0])

    # Setup servo if connected.
    hostname = self.ads[0].serial.split(':')[0]
    self.servo = pasit_device.create_servo(self, hostname)
    if self.servo:
      self.servo.disable_servo_power()

    # Make ADB run as root from the start. Some dts/libtypec actions require
    # this.
    self.dut.adb.root()

    self.passport.save_topology_diagram(self.log_path)

  def teardown_test(self):
    # Reset the tester's state.
    self._set_usb_tester_default_state()
    super().teardown_test()

  def teardown_class(self):
    # Teardown the passport host and UTC-274.
    if getattr(self, 'passport', None):
      self.passport.teardown()
    if getattr(self, 'servo', None):
      self.servo.enable_servo_power()
    super().teardown_class()

  def pre_run(self):
    """Extracts the enabled ports from the tester."""

    # If the PassportHost is not in the contoller configs,
    # then we are just listing the tests.
    if 'PassportHost' not in self.controller_configs:
      logging.warning(
          'PassportHost is not in the controller configs, skipping port'
          ' extraction.'
      )
      self.enabled_ports = [0, 1]
      return

    self.enabled_ports = []
    passport_config = self.controller_configs['PassportHost']
    topology_config = passport_config[0].get('host_topology')
    topology = json_format.ParseDict(
        topology_config, pasit_host_pb2.PasitHost()
    )
    devices = {
        device.id: device
        for device in topology.devices
        if device.type == pasit_host_pb2.PasitHost.Device.Type.USB_TESTER
    }

    for conn in topology.connections:
      if conn.parent_id in devices and conn.parent_port:
        self.enabled_ports.append(int(conn.parent_port))

    logging.info('Enabled ports: %s', self.enabled_ports)

  def _set_usb_tester_default_state(self):
    """Sets the USB tester state."""
    self.utc.active_port = None
    self.utc.pd_init_state = usb.InitPdState.PD_DRP
    self.utc.usb_channel = usb.UsbChannel.USB_3
    self.utc.usb_path = usb.UsbPath.USB_PATH_INTERNAL
    self.utc.source_pdo_count = usb.DEFAULT_SRC_PDO_COUNT

  def generate_test_name(self, params: utc_params.UTCParams) -> str:
    """Generates the test name for the test."""
    flipped = 'flipped' if params.flip else 'normal'
    return f'test_{params.name}_port{params.port}_{flipped}'
