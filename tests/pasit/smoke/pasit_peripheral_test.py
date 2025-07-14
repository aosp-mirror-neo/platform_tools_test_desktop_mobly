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

"""A smoke test that validates PASIT periphal functionality.

These are intended to be the most basic tests that we can run to validate that
the testbed setup is and that all the connections are working.

It is still prone to failure due to things outside of the testbed, however,
these are meant to be the first tests to run when setting up a new testbed or
when a testbed is suspected to be in a bad state to help with debugging.
"""

import logging

from lib.pasit import pasit_storage
from lib.pasit import pasit_test
from lib.utils import retry
from mobly import asserts
from mobly import test_runner


class PasitPeripheralTest(pasit_test.PasitTestClass):

  def test_storage(self):
    """Tests that we can activate and detect all storage devices."""
    # skip if storage is not present in the topology
    asserts.skip_if(
        not self.passport_host.is_device_type_present(
            pasit_test.PasitTestClass.DEVICE_TYPE_STORAGE
        ),
        'Storage device is not present in the topology.',
    )
    storage = self.create(pasit_storage)

    for device in self.passport_host.topology.devices:
      if device.type != pasit_test.PasitTestClass.DEVICE_TYPE_STORAGE:
        continue
      logging.info('Testing storage device: %s', device.id)
      self.passport_host.activate_device_by_id(device.id)
      try:
        mount_point = retry.retry(
            storage.get_external_mount_point,
            until=lambda mount_point: mount_point,
            max_tries=10,
        )
        logging.info('Found storage mount point: %s', mount_point)
      finally:
        self.passport_host.deactivate_device_by_id(device.id)


if __name__ == '__main__':
  test_runner.main()
