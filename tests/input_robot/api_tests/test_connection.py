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
"""Test connections with HMR API and DUT."""

from lib.input_robot import hmr_base_test
from mobly import asserts
from mobly import test_runner

# Each tuple is a list of arguments for a test case.
_TEST_ARGUMENTS: tuple[tuple[str, ...], ...] = (('hello_world',),)


class TestConnection(hmr_base_test.HmrTestClass):
  """HMR connection test."""

  def pre_run(self):
    """Generate tests for each test case."""
    self.generate_tests(test_logic=self.hmr_test_logic,
                        name_func=self.hmr_test_name,
                        arg_sets=_TEST_ARGUMENTS)

  def hmr_test_name(self, name: str) -> str:
    """Get the test name for the given test args."""
    return f'test_hmr_api_connectivity_{name}'

  def hmr_test_logic(self, test_string: str):
    """Basic check to verify communication with HMR."""
    # Test HMR
    hmr_status = self.hmr.test_connection()
    asserts.assert_is_not_none(hmr_status)
    asserts.assert_equal(hmr_status, True)

    # Test DUT
    dut_status = self.dut.adb.shell(f'echo {test_string}')
    asserts.assert_equal(dut_status.strip().decode('utf-8'), test_string)


if __name__ == '__main__':
  test_runner.main()
