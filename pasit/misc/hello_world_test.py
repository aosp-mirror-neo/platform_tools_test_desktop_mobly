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

"""A sample test demonstrating how to run a test on both Android and ChromeOS."""

from mobly import base_test
from mobly import test_runner

from pasit.lib import pasit_device


class HelloWorldTest(base_test.BaseTestClass):

  dut: pasit_device.PasitDevice

  def setup_class(self):
    self.dut = pasit_device.create(self)

  def test_hello(self):
    self.dut.shell(['echo', 'Hello', 'World!'])


if __name__ == '__main__':
  test_runner.main()
