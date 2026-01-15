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

"""Test external storage functionality after formatting in case of plugin."""

import logging

from lib.pasit import peripheral_connector
from lib.utils import functools
from mobly import asserts
from mobly import test_runner
from pasit.storage import write_to_storage_base_test


@functools.generate_tests
class FormatExternalStorageTest(
    write_to_storage_base_test.WriteToStorageBaseTest
):
  """Tests external storage functionality after formatting in case of plugin."""

  @functools.with_variants(
      dock=(peripheral_connector.ConnectionType.DOCK,),
      dockless=(peripheral_connector.ConnectionType.DOCKLESS,),
  )
  def test_format_external_storage(
      self,
      connection_type: peripheral_connector.ConnectionType
  ):
    """Test external storage functionality after formatting."""

    self.plug_in_external_storage(connection_type)

    blkdevs = self._try_get_external_storage_blkdevs()

    asserts.assert_equal(
        len(blkdevs),
        1,
        f'Expected 1 external storage block device, found {len(blkdevs)}.'
    )

    logging.info('Formatting external storage.')
    asserts.assert_true(
        self.storage.format_external_storage(),
        'External storage formatting failed.',
    )

    external_storage_path = self.verify_external_storage_mounted(
        'External storage not mounted after formatting.'
    )

    external_storage_file_path = self.copy_file_to_external_storage(
        self.host_file_path, external_storage_path
    )

    self.verify_test_file_content_matches(
        external_storage_file_path, self.host_file_content
    )


if __name__ == '__main__':
  test_runner.main()
