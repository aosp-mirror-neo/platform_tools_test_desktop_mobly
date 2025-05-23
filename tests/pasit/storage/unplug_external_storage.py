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

"""Test external storage operability after unplugging and replugging."""

import logging
import os

from mobly import asserts
from mobly import test_runner

from lib.pasit import dut_state_manager
from pasit.storage import storage_base_test


# Each tuple is a list of arguments for a test case. The first argument is a
# PowerState indicating the DUT state when external storage is unplugged.
_TEST_ARGUMENTS: tuple[tuple[dut_state_manager.PowerState, ...], ...] = (
    (dut_state_manager.PowerState.ON,),
    (dut_state_manager.PowerState.SUSPEND,),
)


class UnplugExternalStorageTest(storage_base_test.StorageBaseTest):
  """Test external storage operability after unplugging and replugging."""

  def setup_test(self):
    """Handle the setup for the test."""
    super().setup_test()
    self.host_file_content, self.host_file_path = self._create_test_file()

  def teardown_test(self):
    """Handle the teardown for the test."""
    os.remove(self.host_file_path)
    super().teardown_test()

  def pre_run(self):
    """Generate tests for each test case."""
    self.generate_tests(
        test_logic=self.storage_test_logic,
        name_func=self.storage_test_name,
        arg_sets=_TEST_ARGUMENTS,
    )

  def storage_test_name(
      self, state_when_unplug_storage: dut_state_manager.PowerState
  ) -> str:
    """Get the test name for the given test args."""
    return f'test_unplug_storage_when_dut_{state_when_unplug_storage.value}'

  def storage_test_logic(
      self, state_when_unplug_storage: dut_state_manager.PowerState
  ):
    """Generate test logic for a specific dut state.

    Args:
      state_when_unplug_storage: The power state of the DUT when external
        storage is unplugged.

    Write to external storage after unplugging it when DUT is in a specific
    state and then replugging it.
    """
    asserts.skip_if(
        self._requires_servo(state_when_unplug_storage)
        and not self.dut.is_servo_configured(),
        'Servo is not configured.',
    )

    self._plug_in_external_storage()
    self._wait_to_mount_or_reformat_external_storage()

    with dut_state_manager.EnterStateAndReturnToPowerOn(
        self.dut, state_when_unplug_storage
    ):
      self._unplug_external_storage()

    asserts.assert_true(
        self._is_external_storage_unmounted(),
        'External storage not unmounted after unplugging.',
    )

    self._plug_in_external_storage()

    external_storage_path = self._wait_for_external_mount_point()
    asserts.assert_true(
        external_storage_path,
        'External storage not mounted after replugging.',
    )
    logging.info('Using external storage with path: %s', external_storage_path)

    external_storage_file_path = self._copy_file_to_external_storage(
        self.host_file_path, external_storage_path
    )

    self._assert_test_file_content_matches(
        external_storage_file_path, self.host_file_content
    )


if __name__ == '__main__':
  test_runner.main()
