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

"""A basic smoke test that validates communication with the PassportHost."""

from mobly import base_test
from mobly import test_runner
from pasit.lib.passport import passport_host
from chromiumos.test.lab.api import pasit_host_pb2


class PassportHostTest(base_test.BaseTestClass):
  """Tests basic functionality of the PassportHost."""

  def setup_class(self):
    if 'PassportHost' in self.controller_configs:
      self.passport_host = self.register_controller(passport_host)[0]
    else:
      raise ValueError(
          'No PassportHost found for controller config:'
          f' {self.controller_configs}'
      )

  def setup_test(self):
    self.passport_host.reset()

  def teardown_test(self):
    self.passport_host.reset()

  def test_get_switches(self):
    """Tests getting the switches from the PassportHost."""
    for switch_id in self.passport_host.get_switch_ids():
      self.passport_host.log.info('Found switch: %s' % switch_id)

  def test_activate_device_by_type(self):
    """Tests activating a device by type from the PassportHost."""
    self.passport_host.activate_device_by_type(
        pasit_host_pb2.PasitHost.Device.Type.STORAGE
    )


if __name__ == '__main__':
  test_runner.main()
