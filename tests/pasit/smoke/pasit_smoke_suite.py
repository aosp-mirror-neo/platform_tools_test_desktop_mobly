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

"""A suite of tests that exercise PASIT smoke tests."""

from mobly import base_suite
from mobly import config_parser
from mobly import suite_runner

from pasit.smoke import pasit_device_test
from pasit.smoke import passport_host_test

class PasitSmokeSuite(base_suite.BaseSuite):
  """A suite of tests that exercise PASIT smoke tests.

  This suite is designed to run a collection of PASIT smoke tests,
  including tests for device functionality and host-side interactions.
  It ensures that all essential PASIT components are working correctly
  before running more complex tests.
  """

  def setup_suite(self, config: config_parser.TestRunConfig):
    self.add_test_class(
        pasit_device_test.PasitDeviceTest,
    )
    self.add_test_class(
        passport_host_test.PassportHostTest,
    )


def main() -> None:
  suite_runner.run_suite_class()

if __name__ == '__main__':
  main()
