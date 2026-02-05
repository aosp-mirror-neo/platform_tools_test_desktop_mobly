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

"""PASIT HID Suite."""

from mobly import base_suite
from mobly import config_parser
from mobly import suite_runner
from pasit.hid import hid_combo_keys
from pasit.hid import hid_lock_unlock_test
from pasit.hid import hid_wake
from pasit.hid import plug_in_hid


class PasitHIDSuite(base_suite.BaseSuite):
  """PASIT HID Suite, contains all HID tests for PASIT."""

  def setup_suite(self, _: config_parser.TestRunConfig) -> None:
    self.add_test_class(
        hid_combo_keys.HIDComboKeysTests,
    )
    self.add_test_class(
        hid_wake.HIDWakeTest,
    )
    self.add_test_class(
        hid_lock_unlock_test.HIDLockUnlockTest,
    )
    self.add_test_class(
        plug_in_hid.PlugInHIDTest,
    )


def main() -> None:
  suite_runner.run_suite_class()


if __name__ == '__main__':
  main()
