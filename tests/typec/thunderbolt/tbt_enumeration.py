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

"""Thunderbolt enumeration tests."""

import logging

from lib.mobly.typec import thunderbolt_sysfs
from lib.pasit import dut_state_manager
from lib.pasit import pasit_test
from lib.utils import retry
from mobly import asserts
from mobly import test_runner

# Timeout for Thunderbolt enumeration
ENUMERATION_TIMEOUT_SEC = 10
REBOOT_TIMEOUT_SEC = 60
SUSPEND_TIMEOUT_SEC = 30


class ThunderboltEnumerationTest(pasit_test.PasitTestClass):
  """Tests for Thunderbolt enumeration."""

  # We need a docking station for this test.
  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_DOCK

  def setup_class(self):
    super().setup_class()
    self.tb_sysfs = thunderbolt_sysfs.ThunderboltSysfs(self.dut)

    # Find all docks in topology
    docks = self.passport_host.get_device_ids_by_type(self.DEVICE_TYPE_DOCK)
    if not docks:
      asserts.abort_class('No docking station found in the topology.')

    # Use the dock with "tbt3" in the name.
    for dock in docks:
      if 'tbt3' in dock:
        self.dock_id = dock
        break
    else:
      asserts.abort_class(
          'No docking station with "tbt3" in the name found in the topology.'
      )

    self.dock_model = self.passport_host.get_device_by_id(self.dock_id).model
    logging.info('Using dock: %s (Model: %s)', self.dock_id, self.dock_model)

    # Ensure dock is disconnected initially
    self.passport_host.deactivate_device_by_id(self.dock_id)

  def teardown_test(self):
    # Ensure the dock is disconnected at the end of the test/iteration
    self.passport_host.deactivate_device_by_id(self.dock_id)
    super().teardown_test()

  def _wait_for_enumeration(self):
    """Waits for the dock to enumerate."""
    logging.info('Waiting for enumeration...')

    def _check_enumeration():
      # We look for a device that might match the dock model.
      dev_id = self.tb_sysfs.find_device_by_name_substring(self.dock_model)
      if dev_id:
        logging.info('Found enumerated device: %s', dev_id)
        return dev_id
      return None

    dev_id = retry.retry(
        _check_enumeration,
        policy=retry.RetryPolicy(
            max_tries=ENUMERATION_TIMEOUT_SEC, delay_seconds=1
        ),
        until=lambda x: x,
    )

    asserts.assert_is_not_none(dev_id, 'Dock was not found.')
    asserts.assert_equal(
        self.tb_sysfs.get_device_generation(dev_id), 3, 'Dock is not TBT3.'
    )

    logging.info('Dock enumerated successfully.')

  def test_dock_hotplug_enumeration(self):
    """Verifies that a Thunderbolt dock enumerates correctly upon hotplug."""

    # Print present devices for debugging.
    logging.info('Devices present before hotplug:')
    for device in self.tb_sysfs.get_all_devices():
      logging.info('Device: %s', device)

    # Hotplug the dock
    logging.info('Plugging in dock: %s', self.dock_id)
    self.passport_host.activate_device_by_id(self.dock_id)

    # Wait for enumeration
    self._wait_for_enumeration()

  def test_dock_reboot_enumeration(self):
    """Verifies that a Thunderbolt dock enumerates correctly after reboot."""
    # 1. Connect the dock
    self.passport_host.activate_device_by_id(self.dock_id)

    # 2. Reboot the DUT
    logging.info('Rebooting DUT...')
    dut_state_manager.execute_power_action(
        self.dut, dut_state_manager.PowerAction.REBOOT
    )

    # 3. Wait for DUT to come back online
    logging.info('Waiting for DUT to come back online...')
    retry.retry(
        self.dut.is_device_online,
        policy=retry.RetryPolicy(max_tries=REBOOT_TIMEOUT_SEC, delay_seconds=1),
        until=lambda x: x,
    )

    # 4. Verify enumeration after reboot
    self._wait_for_enumeration()

  def test_dock_suspend_enumeration(self):
    """Verifies that a Thunderbolt dock enumerates correctly after suspend."""

    # 1. Connect the dock
    self.passport_host.activate_device_by_id(self.dock_id)
    self._wait_for_enumeration()

    # 2. Suspend and Resume
    logging.info('Suspending DUT...')
    with dut_state_manager.EnterStateAndReturnToPowerOn(
        self.dut, dut_state_manager.PowerState.SUSPEND
    ):
      logging.info('DUT suspended.')

    # 3. Wait for DUT to come back online
    logging.info('Waiting for DUT to come back online...')
    retry.retry(
        self.dut.is_device_online,
        policy=retry.RetryPolicy(
            max_tries=SUSPEND_TIMEOUT_SEC, delay_seconds=1
        ),
        until=lambda x: x,
    )

    # 4. Verify enumeration after resume
    self._wait_for_enumeration()


if __name__ == '__main__':
  test_runner.main()
