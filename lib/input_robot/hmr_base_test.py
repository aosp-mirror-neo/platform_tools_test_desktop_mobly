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
"""Base test class for HMR Mobly tests."""

import logging
import types
from typing import Any

from lib.input_robot import hmr_device
from mobly import base_test
from mobly import records
from mobly import signals
from mobly.controllers import android_device


class HmrTestClass(base_test.BaseTestClass):
  """Base test class for HMR Mobly tests."""

  def setup_class(self):
    """Setup steps before any test is executed."""
    super().setup_class()

    self.dut = self.register_controller(android_device)[0]
    self.hmr = self.register_controller(hmr_device)[0]

  def on_fail(self, record: records.TestResultRecord):
    """Called on test failure."""
    if hasattr(self, 'hmr'):
      hmr_errs = self.hmr.get_errors()
      if hmr_errs:
        logging.debug('HMR errors: %s', hmr_errs)
    super().on_fail(record)

  def create(self, module: types.ModuleType) -> Any:
    """Create a component utility instance for the test Mobly controller.

    Args:
      module: The module must have a field named `registry` which is a
        dictionary of controller type as the key, and corresponding component
        utility class as the value.

    Returns:
      A component utility instance for particular Mobly controller.
    """
    controller = self.dut.controller
    for controller_type, func in module.registry.items():
      if isinstance(controller, controller_type):
        return func(controller)
    raise signals.TestError(
        f'Unknown controller type: {type(controller).__name__}')

  def start_evemu_record(self, input_device: int, log_path: str) -> None:
    """Start logging evemu events in the background.

    Uses `evemu-record` to log the events from input_device while redirecting
    them to the log path. Expected to be run as a subprocess within a test.

    Args:
      input_device: The index of the device to record evemu events from.
      log_path: The path of the log file to write to.
    """
    try:
      evemu_record_cmd = (
          f'evemu-record /dev/input/event{input_device} > {log_path}')
      logging.debug('Starting evemu logging')
      self.dut.adb.shell(evemu_record_cmd)
    # `mobly.signals.TestAbortAll` is raised when terminating this process from
    # the actual test logic (i.e. test_evemu.py) running this function as a
    # subprocess. We catch it here to not cause a test failure.
    except signals.TestAbortAll:
      logging.debug(
          'evemu logging process: Caught TestAbortAll. This is expected.')
