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

"""A suite of tests that exercise PASIT testbed setup."""

from mobly import base_suite
from mobly import config_parser
from mobly import suite_runner
from pasit.smoke import pasit_peripheral_test
from pasit.smoke import pasit_servo_test
from pasit.smoke import passport_host_test


class PasitTestbedSmokeSuite(base_suite.BaseSuite):
  """A suite of tests that exercise PASIT testebed.

  This suite is designed to run a collection of PASIT smoke tests,
  to identify issues with the testbed setup.
  """

  def setup_suite(self, config: config_parser.TestRunConfig):
    self.add_test_class(
        passport_host_test.PassportHostTest,
    )
    self.add_test_class(
        pasit_servo_test.ServoTest,
    )
    self.add_test_class(
        pasit_peripheral_test.PasitPeripheralTest,
    )


def main() -> None:
  suite_runner.run_suite_class()

if __name__ == '__main__':
  main()
