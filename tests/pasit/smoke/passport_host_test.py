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

"""A basic smoke test that validates communication with the PassportHost."""

import logging
from chromiumos.test.lab.api import pasit_host_pb2
from lib.pasit.passport import passport_host
from mobly import asserts
from mobly import base_test
from mobly import test_runner


class PassportHostTest(base_test.BaseTestClass):
  """Tests basic functionality of the PassportHost."""

  def setup_class(self):
    if 'PassportHost' in self.controller_configs:
      self.passport_host = self.register_controller(passport_host)[0]
    else:
      raise ValueError(
          'No PassportHost found for controller config:'
          f' {self.controller_configs}'
      )

  def setup_test(self):
    self.passport_host.reset()

  def teardown_test(self):
    self.passport_host.reset()

  def test_get_switches(self):
    """Tests getting the switches from the PassportHost.

    This also implicitly tests that the switches in the topology are all
    connected, since the __init__ method of passport_host will call
    _validate_topology_switches which will raise an error if any of the
    switches are not connected.
    """
    for switch_id in self.passport_host.get_switch_ids():
      self.passport_host.log.info('Found switch: %s' % switch_id)

  def test_topology_not_empty(self):
    """Tests that the topology is not empty.

    For PASIT tests the topology should always be populated and have at least
    one device and connection. This test is intended to run on PASIT testbeds
    and is not compatible with other testbed that may be similar but have an
    empty topology.
    """
    device_count = len(self.passport_host.topology.devices)
    logging.info('Topology Device count: %s' % device_count)
    asserts.assert_true(
        device_count > 0, 'Expected at least one device in topology.'
    )
    connection_count = len(self.passport_host.topology.connections)
    logging.info('Topology Connection count: %s' % connection_count)
    asserts.assert_true(
        connection_count > 0, 'Expected at least one connection in topology.'
    )

  def test_number_of_cameras(self):
    """Tests that the number of cameras is what we expect based on topology.

    The number of cameras should be equal to number of external displays + 1
    for the internal display.
    """
    external_display_count = sum([
        1 if device.type == pasit_host_pb2.PasitHost.Device.Type.MONITOR else 0
        for device in self.passport_host.topology.devices
    ])
    logging.info('External display count: %s' % external_display_count)
    camera_count = len(self.passport_host.get_cameras())
    logging.info('Camera count: %s' % camera_count)
    asserts.assert_greater_equal(
        camera_count,
        external_display_count + 1,
        'Testbed does not have the expected number of cameras for the'
        f' topology, want >= {external_display_count + 1} got {camera_count}',
    )


if __name__ == '__main__':
  test_runner.main()
