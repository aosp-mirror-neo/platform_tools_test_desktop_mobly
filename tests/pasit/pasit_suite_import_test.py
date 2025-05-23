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

"""Unit test to ensure that there are no import errors."""

import unittest


class PASITSuiteImportTest(unittest.TestCase):

  def setUp(self):
    super().setUp()

  def tearDown(self):
    super().tearDown()

  def test_import_pasit_camera_suite(self):
    from pasit.camera import pasit_camera_suite

  def test_import_pasit_display_suite(self):
    from pasit.display import pasit_display_suite

  def test_import_pasit_smoke_suite(self):
    from pasit.smoke import pasit_smoke_suite

  def test_import_pasit_storage_suite(self):
    from pasit.storage import pasit_storage_suite

if __name__ == '__main__':
  unittest.main()
