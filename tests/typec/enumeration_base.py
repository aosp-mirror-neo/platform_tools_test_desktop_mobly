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

"""Base class for enumeration tests."""

import logging

from lib.mobly.typec import thunderbolt_sysfs
from lib.pasit import dut_state_manager
from lib.pasit import pasit_test
from lib.utils import retry
from mobly import asserts

# Timeout for enumeration
ENUMERATION_MAX_TRIES = 10
REBOOT_TIMEOUT_SEC = 60
SUSPEND_TIMEOUT_SEC = 30


class EnumerationTestBase(pasit_test.PasitTestClass):
  """Base class for enumeration tests."""

  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_DOCK

  def setup_class(self, dock_name_filter: str, generation: int):
    super().setup_class()
    self.tb_sysfs = thunderbolt_sysfs.ThunderboltSysfs(self.dut)
    self.set_dock_filter(dock_name_filter)
    self.generation = generation

  def set_dock_filter(self, dock_name_filter):
    """Sets the dock ID and model based on the filter."""
    # Find all docks in topology
    docks = self.passport_host.get_device_ids_by_type(self.DEVICE_TYPE_DOCK)

    for dock in docks:
      if dock_name_filter in dock:
        self.dock_id = dock
        break
    else:
      asserts.abort_class(
          f'No docking station with "{dock_name_filter}" in the name found.'
      )

    self.dock_model = self.passport_host.get_device_by_id(self.dock_id).model
    logging.info('Using dock: %s (Model: %s)', self.dock_id, self.dock_model)

    # Ensure dock is disconnected initially
    self.passport_host.deactivate_device_by_id(self.dock_id)

  def teardown_test(self):
    # Ensure the dock is disconnected at the end of the test/iteration
    if self.dock_id:
      self.passport_host.deactivate_device_by_id(self.dock_id)
    super().teardown_test()

  def _wait_for_enumeration(self):
    """Waits for the dock to enumerate."""
    logging.info('Waiting for enumeration...')

    dev_id = retry.retry(
        lambda: self.tb_sysfs.find_device_by_name_substring(self.dock_model),
        policy=retry.RetryPolicy(
            max_tries=ENUMERATION_MAX_TRIES, delay_seconds=1
        ),
        until=lambda x: x,
    )

    asserts.assert_is_not_none(dev_id, 'Dock was not found.')
    logging.info('Found enumerated device: %s', dev_id)
    asserts.assert_equal(
        self.tb_sysfs.get_device_generation(dev_id),
        self.generation,
        'Generation mismatch',
    )

    logging.info('Dock enumerated successfully.')

  def test_dock_hotplug_enumeration(self):
    """Verifies that a dock enumerates correctly upon hotplug."""

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
    """Verifies that a dock enumerates correctly after reboot."""
    # 1. Connect the dock
    self.passport_host.activate_device_by_id(self.dock_id)

    # 2. Reboot the DUT
    logging.info('Rebooting DUT...')
    dut_state_manager.execute_power_action(
        self.dut, dut_state_manager.PowerAction.REBOOT
    )

    # 3. Verify enumeration after reboot
    self._wait_for_enumeration()

  def test_dock_suspend_enumeration(self):
    """Verifies that a dock enumerates correctly after suspend/resume."""

    # 1. Connect the dock
    self.passport_host.activate_device_by_id(self.dock_id)
    self._wait_for_enumeration()

    # 2. Suspend and Resume
    logging.info('Suspending DUT...')
    dut_state_manager.execute_power_action(
        self.dut, dut_state_manager.PowerAction.SUSPEND
    )

    # 3. Verify enumeration after resume
    self._wait_for_enumeration()
