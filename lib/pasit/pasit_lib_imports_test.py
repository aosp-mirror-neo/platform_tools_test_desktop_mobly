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

"""Unit test to ensure that the PASIT library works without any errors."""

import unittest
# pylint: disable=g-import-not-at-top,unused-import


class PASITLibImportsTest(unittest.TestCase):
  """Unit test to ensure that the PASIT library works without any errors.

  Since python in Android does not do any dependency checking this is a simple
  test to ensure that the library works without any if any libraries or their
  dependencies are missing this should fail and catch the error.
  """

  def setUp(self):
    super().setUp()

  def tearDown(self):
    super().tearDown()

  def test_import_pasit_device(self):
    from lib.pasit import pasit_device

  def test_import_pasit_camera(self):
    from lib.pasit import pasit_camera

  def test_import_pasit_display(self):
    from lib.pasit import pasit_display

  def test_import_pasit_file(self):
    from lib.pasit import pasit_file

  def test_import_pasit_storage(self):
    from lib.pasit import pasit_storage

  def test_import_pasit_test(self):
    from lib.pasit import pasit_test

  def test_import_pasit_pasport(self):
    from lib.pasit.passport import passport_host

if __name__ == '__main__':
  unittest.main()
