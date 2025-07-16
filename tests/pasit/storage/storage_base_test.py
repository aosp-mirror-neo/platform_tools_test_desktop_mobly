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

"""Base test for tests that use external storage."""

import logging
from os import path
import random
import string
import tempfile

from lib.pasit import pasit_file
from lib.pasit import pasit_storage
from lib.pasit import pasit_test
from lib.utils import retry
from mobly import asserts
from mobly import signals


_DUT_TMP_DIR = '/data/local/tmp/'


class StorageBaseTest(pasit_test.PasitTestClass):
  """Base test for tests that use external storage."""

  storage: pasit_storage.PasitStorage
  file_interface: pasit_file.PasitFile
  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_STORAGE

  def setup_class(self):
    """Handle the setup for the test.

    Create PasitStorage for the interacting with external storage.
    """
    super().setup_class()
    self.storage = self.create(pasit_storage)
    self.file_interface = self.create(pasit_file)

  def _plug_in_external_storage(self):
    """Emulate external storage plug in using passport."""
    logging.info('Plugging in external storage')
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_STORAGE)

  def _unplug_external_storage(self):
    """Emulate external storage unplug using passport."""
    logging.info('Unplugging external storage')
    self.passport_host.deactivate_device_by_type(self.DEVICE_TYPE_STORAGE)

  def _wait_to_mount_or_reformat_external_storage(self) -> str:
    """Wait to mount or reformat the external storage.

    Returns:
      The path to the external storage. Use the first mount point as the
      external storage path for testing.

    Raises:
      TestError: If no external storage is found.
    """
    logging.info('Waiting for external storage to mount')
    mount_point = self._wait_for_external_mount_point()

    if not mount_point:
      logging.info('External storage not mounted, formatting and trying again.')
      if not self.storage.format_external_storage():
        raise signals.TestError(
            'Formatting external storage failed: no USB storage device found.'
        )

      # Unplug and replug the external storage to ensure that the storage is
      # mounted after formatting.
      self._unplug_external_storage()
      self._plug_in_external_storage()
      mount_point = self._wait_for_external_mount_point()
    return mount_point

  def _create_test_file(self, size: int = 1024) -> tuple[str, str]:
    """Creates a test file with a string of random characters.

    Args:
      size: The size of the test file in bytes.

    Returns:
      The random test string and the path to the test file.
    """

    # Make a test string of random characters.
    test_string = ''.join(
        random.choice(string.ascii_letters + string.digits) for _ in range(size)
    )

    with tempfile.NamedTemporaryFile(
        prefix='storage_test_',
        suffix='.txt',
        delete=False,
        mode='w',
    ) as test_file:
      test_file.write(test_string)
      return test_string, test_file.name

  def _get_test_file_content(self, test_file_path: str) -> str:
    """Gets the content of a file.

    Args:
      test_file_path: The path to the file.

    Returns:
      The content of the file.
    """
    # Open the file in the host tmp directory for reading.
    with open(test_file_path, 'r') as test_file:
      return test_file.read()

  def _assert_test_file_content_matches(
      self, external_storage_file_path: str, expected_file_content: str
  ) -> None:
    """Asserts that the content of the test file matches.

    Asserts that the content of the test file matches the expected file content
    by reading the file from the external storage.

    Args:
      external_storage_file_path: The path to the file on the external storage.
      expected_file_content: The expected content of the file.
    """
    with tempfile.TemporaryDirectory(prefix='storage_test_') as temp_dir:
      host_copy_file_path = self._pull_file_from_external_storage(
          external_storage_file_path, temp_dir
      )
      asserts.assert_equal(
          self._get_test_file_content(host_copy_file_path),
          expected_file_content,
          'File content does not match after reading from external storage.',
      )

  def _copy_file_to_external_storage(
      self, host_file_path: str, external_storage_path: str
  ) -> str:
    """Copies a file from the host to the external storage.

    Args:
      host_file_path: The path to the file on the host.
      external_storage_path: The path to the external storage.

    Returns:
      The path to the file on the external storage.
    """
    file_name = path.basename(host_file_path)
    dut_file_path = path.join(_DUT_TMP_DIR, file_name)
    logging.info(
        'Copying file from host [%s] to DUT [%s]',
        host_file_path,
        dut_file_path,
    )
    self.file_interface.push_file(host_file_path, dut_file_path)

    external_storage_file_path = path.join(external_storage_path, file_name)
    logging.info(
        'Copying file from DUT [%s] to external storage [%s]',
        dut_file_path,
        external_storage_file_path,
    )
    self.file_interface.copy_file(dut_file_path, external_storage_file_path)
    return external_storage_file_path

  def _pull_file_from_external_storage(
      self,
      external_storage_file_path: str,
      temp_dir: str,
      delete_from_storage: bool = True,
  ) -> str:
    """Pulls a file from the external storage to the host.

    Args:
      external_storage_file_path: The path to the file on the external storage.
      temp_dir: The temporary directory on the host into which the test file
        will be copied.
      delete_from_storage: Whether to delete the file from the external storage
        after pulling it.

    Returns:
      The path to the file on the host.
    """
    host_file_path = path.join(
        temp_dir, path.basename(external_storage_file_path)
    )

    logging.info(
        'Copying file from external storage [%s] to host [%s]',
        external_storage_file_path,
        host_file_path,
    )
    self.file_interface.pull_file(
        external_storage_file_path,
        host_file_path,
    )

    if delete_from_storage:
      logging.info(
          'Deleting file from external storage [%s]',
          external_storage_file_path,
      )
      self.file_interface.remove_file(external_storage_file_path)
    return host_file_path

  def _wait_for_external_mount_point(self, max_tries: int = 10) -> str:
    """Blocks until an external removable storage mount point is found.

    Args:
      max_tries: The maximum number of times to check for the mount point.

    Returns:
      A path for the external removable storage.
    """
    return retry.retry(
        self.storage.get_external_mount_point,
        until=lambda mount_point: mount_point,
        max_tries=max_tries,
    )

  def _is_external_storage_mounted(self) -> bool:
    return bool(self._wait_for_external_mount_point())

  def _is_external_storage_unmounted(self, max_tries: int = 10) -> bool:
    """Blocks until an external removable storage mount point is unmounted.

    Use this method to wait for the external storage to be unmounted after
    unplugging to avoid retry failed message and test timeout.

    Args:
      max_tries: The maximum number of times to check for the mount point.

    Returns:
      True if the external removable storage is unmounted, False otherwise.
    """
    return retry.retry(
        lambda: not self.storage.get_external_mount_point(),
        until=lambda unmounted: unmounted,
        max_tries=max_tries,
    )
