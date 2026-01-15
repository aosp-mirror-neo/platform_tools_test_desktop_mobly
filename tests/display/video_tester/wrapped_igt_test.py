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

"""Wrapped IGT Test."""

import logging
from typing import Sequence

from display.utils import wrapped_display_base_test
from lib.pasit.base import base_pasit_device
from lib.utils import functools
from mobly import base_suite
from mobly import config_parser
from mobly import suite_runner

# Test modules to run.
_TEST_MODULES: Sequence[str] = ['IgtKmsAtomicTestCases']

# Additional data modules to run that need to be installed along-side of the
# test modules.
_DATA_MODULES: Sequence[str] = ['kms_atomic64']


@functools.generate_tests
class WrappedIgtTest(wrapped_display_base_test.WrappedDisplayBaseTest):
  """Test class for wrapped IGT tests."""

  _STOP_SERVICES = (
      'vendor.hwcomposer-3',
      'vendor.hwcomposer-2-4',
      'vendor.qti.hardware.display.composer')

  native_modules: Sequence[str] = _TEST_MODULES + _DATA_MODULES

  def setup_test(self) -> None:
    super().setup_test()
    for service in self._STOP_SERVICES:
      try:
        self.dut.shell(['stop', service])
      except base_pasit_device.ShellError as e:
        logging.warning('failed to stop service: %s: %s', service, e)

  def teardown_test(self) -> None:
    for service in self._STOP_SERVICES:
      try:
        self.dut.shell(['start', service])
      except base_pasit_device.ShellError as e:
        logging.warning('failed to start service: %s: %s', service, e)
    super().teardown_test()

  def get_install_path(self, module_name: str) -> str:
    """Gets the installation path for a module.

    Args:
      module_name: The name of the module.

    Returns:
      The path where the module should be installed.
    """
    # Non-test data modules should go in /data/igt_tests, see:
    #   platform_testing/tests/display/igt/igt_config_template.xml
    if module_name in _DATA_MODULES:
      return f'/data/igt_tests/{module_name}'
    return super().get_install_path(module_name)

  @functools.with_variants(**{k: (k,) for k in _TEST_MODULES})
  def test_wrapped(self, module) -> None:
    """Runs testcases in the provided module."""
    self.run_all_gtest_test(self.get_install_path(module))


class WrappedIgtSuite(base_suite.BaseSuite):
  """Wrapped IGT test suite."""

  def setup_suite(self, config: config_parser.TestRunConfig) -> None:
    self.add_test_class(WrappedIgtTest)


def main() -> None:
  suite_runner.run_suite_class()


if __name__ == '__main__':
  main()
