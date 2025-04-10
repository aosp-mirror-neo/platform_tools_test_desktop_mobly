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

"""Test writing to a file in external storage."""

import logging
import random
import string
import tempfile

from mobly import asserts
from mobly import test_runner

from pasit.lib import pasit_file
from pasit.storage import storage_base_test


class WriteToExternalStorageTest(storage_base_test.StorageBaseTest):
  """Test writing to a file in external storage."""

  HOST_COPY_FILE_PATH = '/tmp/write_to_external_storage_copy.txt'
  DUT_FILE_NAME = 'write_to_external_storage.txt'

  def setup_class(self):
    """Handle the setup for the test."""
    super().setup_class()
    self.file_interface = self.create(pasit_file)
    self.host_file_content, self.host_file_path = self._create_test_file()

  def test_write(self):
    """Run the test."""
    self._plug_in_external_storage()

    external_storage_path = self._wait_to_mount_or_reformat_external_storage()
    logging.info('Using external storage with path: %s', external_storage_path)

    exernal_storage_file_path = f'{external_storage_path}/{self.DUT_FILE_NAME}'
    logging.info(
        'Copying file from host [%s] to external storage [%s]',
        self.host_file_path,
        exernal_storage_file_path,
    )
    self.file_interface.push_file(
        self.host_file_path, exernal_storage_file_path
    )

    logging.info(
        'Copying file from external storage [%s] to host [%s]',
        exernal_storage_file_path,
        self.HOST_COPY_FILE_PATH,
    )
    self.file_interface.pull_file(
        exernal_storage_file_path,
        self.HOST_COPY_FILE_PATH,
    )

    asserts.assert_true(
        self._verify_test_file_content(
            self.HOST_COPY_FILE_PATH, self.host_file_content
        ),
        'File content does not match after reading from external storage.',
    )

  def _create_test_file(self) -> tuple[str, str]:
    """Creates a test file with a 1KB string of random characters.

    Returns:
      The random test string and the path to the test file.
    """

    # Make a 1KB test string of random characters.
    test_string = ''.join(
        random.choice(string.ascii_letters + string.digits) for _ in range(1024)
    )

    # Create file in host tmp directory (if it doesn't exist),
    # or overwrite it if it does exist.
    with tempfile.NamedTemporaryFile(
        prefix='write_to_external_storage_test',
        suffix='.txt',
        delete=False,
        mode='w',
    ) as test_file:
      test_file.write(test_string)
      return test_string, test_file.name

  def _verify_test_file_content(self, path: str, expected_content: str) -> bool:
    """Verifies that the test file contains the correct data.

    Args:
      path: The path to the test file.
      expected_content: The expected content of the test file.

    Returns:
      True if the test file contains the correct data, False otherwise.
    """
    # Open the file in the host tmp directory for reading.
    with open(path, 'r') as f:
      content = f.read()
    if content != expected_content:
      logging.info('Expected:\n%s\n, Actual:\n%s\n', expected_content, content)
      return False
    return True


if __name__ == '__main__':
  test_runner.main()
