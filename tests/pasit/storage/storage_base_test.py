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

from lib.pasit import pasit_storage
from lib.pasit import pasit_test
from lib.pasit import test_policy
from lib.utils import retry
from mobly import asserts
from mobly import signals


class StorageBaseTest(pasit_test.PasitTestClass):
  """Base test for tests that use external storage."""

  storage: pasit_storage.PasitStorage
  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_STORAGE

  def setup_class(self):
    """Handle the setup for the test.

    Create PasitStorage for the interacting with external storage.
    """
    super().setup_class()
    self.storage = self.create(pasit_storage)

  def plug_in_external_storage(self):
    """Emulate external storage plug in using passport."""
    logging.info('Plugging in external storage')
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_STORAGE)

  def unplug_external_storage(self):
    """Emulate external storage unplug using passport."""
    logging.info('Unplugging external storage')
    self.passport_host.deactivate_device_by_type(self.DEVICE_TYPE_STORAGE)

  def verify_external_storage_mounted_or_reformat(self, message: str) -> str:
    """Wait to mount, reformat and retry if failed.

    Returns:
      The path to the external storage. Use the first mount point as the
      external storage path for testing.

    Raises:
      TestError: If formatting external storage failed.
    """
    blkdevs = self._try_get_external_storage_blkdevs()
    if not blkdevs:
      raise signals.TestError('No external storage device found.')
    elif len(blkdevs) > 1:
      raise signals.TestError(
          f'Expected exactly one external storage disk, got {len(blkdevs)}:'
          f' {blkdevs}.',
      )
    mount_point = self._try_get_external_mount_point()
    if not mount_point:
      logging.info('External storage not mounted, formatting and trying again.')
      if not self.storage.format_external_storage():
        raise signals.TestError(
            'Formatting external storage failed: no USB storage device found.'
        )
      mount_point = self._try_get_external_mount_point()

    asserts.assert_true(mount_point, message)
    logging.info('External storage mounted at: %s', mount_point)
    return mount_point

  def _try_get_external_mount_point(self) -> str:
    """Blocks until an external removable storage mount point is found.

    Returns:
      A path for the external removable storage. Empty string if not found.
    """
    logging.info('Waiting for external storage to mount...')
    return retry.retry(
        self.storage.get_external_mount_point,
        until=lambda mount_point: mount_point,
        policy=test_policy.StorageTestPolicy.EXTERNAL_STORAGE_MOUNTED_RETRY_POLICY,
    )

  def _try_get_external_storage_blkdevs(self) -> list[str]:
    """Blocks until an external removable storage block device is found."""
    logging.info('Waiting for external storage to be detected...')
    return retry.retry(
        self.storage.get_external_storage_blkdevs,
        until=lambda blkdevs: blkdevs,
        policy=test_policy.StorageTestPolicy.EXTERNAL_STORAGE_DETECTED_RETRY_POLICY,
    )

  def verify_external_storage_mounted(self, message: str) -> str:
    """Blocks until an external removable storage is mounted."""
    mount_point = self._try_get_external_mount_point()
    asserts.assert_true(mount_point, message)
    logging.info('External storage mounted at: %s.', mount_point)
    return mount_point

  def verify_external_storage_unmounted(self, message: str) -> None:
    """Blocks until an external removable storage is unmounted.

    Asserts that the external removable storage is unmounted.
    """
    logging.info('Waiting for external storage to unmount...')
    asserts.assert_false(
        retry.retry(
            lambda: self.storage.get_external_mount_point(),
            until=lambda mount_point: not mount_point,
            policy=test_policy.StorageTestPolicy.EXTERNAL_STORAGE_UNMOUNTED_RETRY_POLICY,
        ),
        message,
    )
    logging.info('External storage unmounted.')

  def eject_external_storage(self) -> bool:
    """Eject external storage."""
    logging.info('Ejecting external storage...')
    if not self.storage.eject_external_storage():
      return False
    logging.info('External storage ejected.')
    return True
