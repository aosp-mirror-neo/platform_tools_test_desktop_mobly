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

"""Test ejecting and re-inserting external storage."""

import logging

from mobly import asserts
from mobly import test_runner

from pasit.storage import storage_base_test

# Each tuple is a list of arguments for a test case. The first argument is a
# boolean indicating whether to reboot the DUT before ejecting the storage.
_TEST_ARGUMENTS: tuple[tuple[bool, ...], ...] = ((False,), (True,))


class EjectExternalStorageTest(storage_base_test.StorageBaseTest):
  """Test ejecting and re-inserting external storage after a reboot."""

  def pre_run(self):
    """Generate tests for each test case."""
    self.generate_tests(
        test_logic=self.eject_test_logic,
        name_func=self.eject_test_name,
        arg_sets=_TEST_ARGUMENTS,
    )

  def eject_test_name(self, reboot: bool) -> str:
    """Get the test name for the given test args."""
    return 'test_eject_after_reboot' if reboot else 'test_mount_and_eject'

  def eject_test_logic(self, reboot: bool):
    """Run the test."""
    self._plug_in_external_storage()

    external_storage_path = self._wait_to_mount_or_reformat_external_storage()
    logging.info('Using external storage with path: %s', external_storage_path)

    if reboot:
      # Reboot the DUT to simulate inserting external storage while the DUT is
      # powered off.
      logging.info('Rebooting DUT')
      self.dut.reboot()
      logging.info('DUT rebooted')
      asserts.assert_true(
          self._is_external_storage_mounted(),
          'External storage not mounted after reboot.',
      )

    # Eject the external storage will fail if the storage is not mounted.
    logging.info('Ejecting external storage')
    asserts.assert_true(
        self.storage.eject_external_storage(),
        'Failed to eject external storage after reboot.',
    )

    asserts.assert_true(
        self._is_external_storage_unmounted(),
        'External storage not unmounted after ejecting.',
    )
    logging.info('External storage unmounted.')

    self._unplug_external_storage()
    self._plug_in_external_storage()

    asserts.assert_true(
        self._is_external_storage_mounted(),
        'External storage not mounted after re-plugging.',
    )


if __name__ == '__main__':
  test_runner.main()
