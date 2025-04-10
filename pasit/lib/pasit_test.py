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

"""Base test class for PASIT Mobly tests."""

import types
from typing import Any

from mobly import base_test

from pasit.lib import pasit_device
from pasit.lib.passport import passport_host
from chromiumos.test.lab.api import pasit_host_pb2


class PasitTestClass(base_test.BaseTestClass):
  """Base test class for PASIT Mobly tests."""

  DEVICE_TYPE_STORAGE = pasit_host_pb2.PasitHost.Device.Type.STORAGE
  DEVICE_TYPE_CAMERA = pasit_host_pb2.PasitHost.Device.Type.CAMERA

  dut: pasit_device.PasitDevice

  def setup_class(self):
    """Handle PASIT specific setup for the test.

    Create PasitDevice controller for the DUT, Passport controller for Passport
    host.
    """
    self.dut = pasit_device.create(self)

    self.passport_host = self._create_passport_controller()
    self.passport_host.reset()

  def teardown_test(self):
    """Any PASIT specific teardown steps."""
    # ensure that the passport switches are disabled after the test
    self.passport_host.reset()

  def create(self, module: types.ModuleType) -> Any:
    """Create a component utility instance for the test Mobly controller.

    Args:
      module: The module must have a field named `_registry` which is a
        dictionary of controller type as the key, and corresponding component
        utility class as the value.

    Returns:
      A component utility instance for particular Mobly controller.
    """
    controller = self.dut.controller
    for controller_type, func in module._registry.items():
      if controller_type == type(controller):
        return func(controller)
    raise ValueError(f'Unknown controller type: {type(controller).__name__}')

  def _create_passport_controller(self) -> passport_host.PassportHost:
    """Create passport host controller from the testbed configuration."""
    if 'PassportHost' in self.controller_configs:
      return self.register_controller(passport_host)[0]
    else:
      raise ValueError(
          'No PassportHost found for controller config:'
          f' {self.controller_configs}'
      )
