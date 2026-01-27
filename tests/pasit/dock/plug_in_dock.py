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

"""Test that plugs in dock when DUT is in different states."""

import logging

from chromiumos.test.lab.api import pasit_host_pb2
from lib.pasit import display_helper
from lib.pasit import dut_state_manager
from lib.pasit import pasit_display
from lib.pasit import pasit_network
from lib.pasit import pasit_storage
from lib.pasit import pasit_test
from lib.pasit import peripheral_connector
from lib.pasit import test_policy
from lib.utils import functools
from lib.utils import retry
from mobly import asserts
from mobly import test_runner


@functools.generate_tests
class PlugInDockTest(pasit_test.PasitTestClass):
  """Tests functionality when attaching a dock with connected peripherals."""

  display: pasit_display.PasitDisplay
  network: pasit_network.PasitNetwork
  storage: pasit_storage.PasitStorage
  helper: display_helper.DisplayHelper
  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_NETWORK

  def setup_class(self):
    """Handle setup: initialize connector and base logic."""
    super().setup_class()
    self.connector = peripheral_connector.PeripheralConnector(
        self.passport_host
    )
    self.display = self.create(pasit_display)
    self.storage = self.create(pasit_storage)
    self.network = self.create(pasit_network)
    self.helper = display_helper.DisplayHelper(self.display)

  def setup_test(self):
    """Setup steps before each test is executed."""
    super().setup_test()
    self.dut.disable_servo_power()

  def teardown_test(self):
    """Handle the teardown for the test."""
    super().teardown_test()
    self.dut.enable_servo_power()

  def teardown_class(self):
    """Handle teardown: cleanup network."""
    super().teardown_class()
    if hasattr(self, 'network'):
      self.network.cleanup()

  @functools.with_variants(
      suspend=(dut_state_manager.PowerAction.SUSPEND,),
      shutdown=(dut_state_manager.PowerAction.SHUTDOWN,),
      reboot=(dut_state_manager.PowerAction.REBOOT,),
  )
  def test_plug_in_dock_and_then(
      self, action_after_plug_in_dock: dut_state_manager.PowerAction
  ):
    """Scenario: Plug dock while ON, then cycle to target power state."""
    self._plug_in_dock_peripherals()
    dut_state_manager.execute_power_action(self.dut, action_after_plug_in_dock)
    self._verify_dock_peripherals()

  @functools.with_variants(
      on=(dut_state_manager.PowerState.ON,),
      off=(dut_state_manager.PowerState.OFF,),
      suspended=(dut_state_manager.PowerState.SUSPEND,),
  )
  def test_plug_in_dock_when_dut(
      self, state_when_plug_dock: dut_state_manager.PowerState
  ):
    """Scenario: Change DUT state first, then plug dock while in that state."""

    with dut_state_manager.EnterStateAndReturnToPowerOn(
        self.dut, state_when_plug_dock
    ):
      self._plug_in_dock_peripherals()
    self._verify_dock_peripherals()

  def plug_in_device_via_dock(
      self, device_type: pasit_host_pb2.PasitHost.Device.Type
  ):
    """Finds and activates a specific device type on the dock."""
    tag = self.connector.get_peripheral_path_tag(
        device_type, peripheral_connector.ConnectionType.DOCK
    )
    logging.info(
        'Plugging in device via dock: %s',
        pasit_test.get_device_type_name(device_type),
    )
    self.passport_host.activate_device_by_type(device_type, tag)

  def _plug_in_dock_peripherals(self):
    """plug in all dock peripherals."""
    self.plug_in_device_via_dock(self.DEVICE_TYPE_MONITOR)
    self.plug_in_device_via_dock(self.DEVICE_TYPE_NETWORK)
    self.plug_in_device_via_dock(self.DEVICE_TYPE_STORAGE)

  def _verify_dock_peripherals(self):
    asserts.assert_true(
        self.dut.is_powered(), 'DUT is not powered or charging.'
    )
    self._verify_external_storage_mounted(
        'External storage not mounted after plugging in the Dock'
    )
    self.helper.get_display_count(expected_display_count=2)
    self._verify_dock_ethernet_interface_is_active()

  def _verify_dock_ethernet_interface_is_active(self):
    """Verifies that single Ethernet interfaces have a physical link."""
    networks = self.network.get_network_infos()
    active_eth_count = 0
    found_names = []

    for network in networks.values():
      if network.name.lower().startswith('eth'):
        logging.info(
            'Checking physical Ethernet: %s (State: %s)',
            network.name,
            network.state,
        )
        if network.state == pasit_network.NetworkState.UP:
          active_eth_count += 1
          found_names.append(network.name)

    asserts.assert_equal(
        active_eth_count,
        1,
        f'Expected 1 active Ethernets, but found {active_eth_count}. '
        f'Active ports: {found_names}',
    )

  def _verify_external_storage_mounted(self, message: str):
    logging.info('Waiting for external storage to mount...')
    mount_point = retry.retry(
        self.storage.get_external_mount_point,
        until=lambda mount_point: mount_point,
        policy=test_policy.StorageTestPolicy.EXTERNAL_STORAGE_MOUNTED_RETRY_POLICY,
    )
    asserts.assert_true(mount_point, message)
    logging.info('External storage mounted at: %s.', mount_point)


if __name__ == '__main__':
  test_runner.main()
