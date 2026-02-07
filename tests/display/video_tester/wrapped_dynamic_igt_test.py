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

"""Wrapped Dynamic IGT Test."""

from typing import Sequence

from chromiumos.test.lab.api import pasit_host_pb2
from display.utils import wrapped_display_base_test
from lib.utils import functools
from mobly import test_runner


# Test modules to run.
_TEST_MODULES: Sequence[str] = ['IgtKmsAtomicTestCases']

# Additional data modules to run that need to be installed along-side of the
# test modules.
_DATA_MODULES: Sequence[str] = ['kms_atomic64']


@functools.generate_tests
class WrappedDynamicIgtTest(wrapped_display_base_test.WrappedDisplayBaseTest):
  """Test class for wrapped IGT tests with dynamic UCD Path."""

  stop_services = (
      'vendor.hwcomposer-3',
      'vendor.hwcomposer-2-4',
      'vendor.qti.hardware.display.composer')

  native_modules: Sequence[str] = _TEST_MODULES + _DATA_MODULES
  # Don't configure any displays.
  num_default_displays: int = 0

  def setup_test(self) -> None:
    super().setup_test()
    self.passport_host.activate_device_by_type(
        pasit_host_pb2.PasitHost.Device.Type.VIDEO_TESTER, None
    )

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


if __name__ == '__main__':
  test_runner.main()
