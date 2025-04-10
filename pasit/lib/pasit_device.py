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

"""The module for PASIT device related imports and types."""

import types
from typing import Any
from mobly import base_test
from mobly.controllers import android_device
from pasit.lib.android import android_pasit_device
from pasit.lib.base import base_pasit_device


PasitDevice = base_pasit_device.BasePasitDevice


def create_controller(
    test_class: base_test.BaseTestClass, controller_module: types.ModuleType
) -> Any:
  """Creates a controller for the given test class and controller module."""
  return test_class.register_controller(controller_module)[0]


def create(test_class: base_test.BaseTestClass) -> PasitDevice:
  """Creates a PasitDevice for the given test class."""
  if 'AndroidDevice' in test_class.controller_configs:
    return android_pasit_device.AndroidPasitDevice(
        create_controller(test_class, android_device)
    )
  else:
    raise ValueError(
        'No device type found for controller config:'
        f' {test_class.controller_configs}'
    )
