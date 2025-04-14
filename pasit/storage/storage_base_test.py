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

from pasit.lib import pasit_storage
from pasit.lib import pasit_test


_STORAGE_MOUNT_TIMEOUT_PARAM = 'storage_mount_timeout'
_STORAGE_MOUNT_TIMEOUT_DEFAULT = 10


class StorageBaseTest(pasit_test.PasitTestClass):
  """Base test for tests that use external storage."""

  removable_storage: pasit_storage.PasitStorage

  def setup_class(self):
    """Handle the setup for the test.

    Create PasitStorage for the interacting with external storage.
    """
    super().setup_class()
    self.removable_storage = self.create(pasit_storage)

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
      ValueError: If no external storage is found.
    """
    logging.info('Waiting for external storage to mount')
    storage_mount_timeout = self._get_storage_mount_timeout()
    try:
      mount_point = self.removable_storage.wait_for_external_mount_point(
          storage_mount_timeout
      )
    except TimeoutError as e:
      logging.info('External storage not mounted, formatting and trying again.')
      if not self.removable_storage.format_external_storage():
        raise ValueError(
            'No USB storage device found, ensure that external storage is'
            ' plugged in and connected to the DUT through switch.'
        ) from e

      # Unplug and replug the external storage to ensure that the storage is
      # mounted after formatting.
      self._unplug_external_storage()
      self._plug_in_external_storage()
      mount_point = self.removable_storage.wait_for_external_mount_point(
          storage_mount_timeout
      )
    return mount_point

  def _get_storage_mount_timeout(self) -> int:
    """Get the storage mount timeout from the user params."""
    return self.user_params.get(
        _STORAGE_MOUNT_TIMEOUT_PARAM, _STORAGE_MOUNT_TIMEOUT_DEFAULT
    )
