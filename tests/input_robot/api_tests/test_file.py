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

from lib.input_robot import hmr_base_test
from mobly import asserts
from mobly import test_runner


class TestFileUploadAndDelete(hmr_base_test.HmrTestClass):
  """HMR API file test.

  Tests 3 different parts of the API - Upload, Existence Check, and Deletion.
  """

  _TEST_ARGUMENTS: tuple[tuple[str, str], ...] = (('test.txt', 'Hello World!'),)

  def pre_run(self):
    """Generate tests for each test case."""
    self.generate_tests(test_logic=self.hmr_test_logic,
                        name_func=self.hmr_test_name,
                        arg_sets=self._TEST_ARGUMENTS)

  def hmr_test_name(self, name: str, _: str) -> str:
    """Get the test name for the given test args."""
    return f'test_upload_file_\'{name}\'_and_delete'

  def hmr_test_logic(self, file_name: str, file_content: str):
    """Upload and delete a file on HMR."""
    upload_status = self.hmr.upload_file(file_name,
                                         file_content.encode('utf-8'))
    asserts.assert_true(upload_status, 'Failed to upload file.')

    file_status = self.hmr.file_exists(file_name)
    asserts.assert_is_not_none(file_status)
    asserts.assert_equal(file_status, True, 'File does not exist on HMR.')

    delete_status = self.hmr.delete_file(file_name)
    asserts.assert_true(delete_status, 'Failed to delete file.')


if __name__ == '__main__':
  test_runner.main()
