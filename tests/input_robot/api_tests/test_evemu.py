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
"""Test that to verify file exists on HMR."""

import multiprocessing
import time
from lib.input_robot import hmr_base_test
from mobly import asserts
from mobly import test_runner


class TestEvemuRecord(hmr_base_test.HmrTestClass):
  """HMR evemu test."""

  _TEST_ARGUMENTS: tuple[tuple[int, str],
                         ...] = ((5, '/data/local/tmp/test-evemu.log'),)

  def pre_run(self):
    """Generate tests for each test case."""
    self.generate_tests(test_logic=self.hmr_test_logic,
                        name_func=self.hmr_test_name,
                        arg_sets=self._TEST_ARGUMENTS)

  def hmr_test_name(self, input_dev: int, logging_path: str) -> str:
    """Get the test name for the given test args."""
    return 'test_evemu'

  def hmr_test_logic(self, input_dev: int, logging_path: str) -> None:
    """Log in the background on HMR."""
    evemu_logging = multiprocessing.Process(target=self.start_evemu_record,
                                            args=(input_dev, logging_path),
                                            daemon=True)

    print('== Start logging evemu ==')
    evemu_logging.start()

    print('== Sleep for 15 seconds to simulate actual test ==')
    time.sleep(15)

    print('== Terminiate the logging process ==')
    evemu_logging.terminate()

    print('== Pull the file from the DUT ==')
    self.dut.adb.pull([logging_path, './test-evemu.log'])

    print('== Check contents of file ==')
    with open('./test-evemu.log', 'r') as f:
      lines = f.readlines()
      print(f'== length of file: {len(lines)} ==')
      asserts.assert_greater(lines, 0)


if __name__ == '__main__':
  test_runner.main()
