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

"""Verify external keyboard functionality after lock/unlock on DUT."""

import logging

from lib.pasit import hid_keys
from mobly import test_runner
from pasit.hid import hid_base_test


class HIDLockUnlockTest(hid_base_test.HIDBaseTest):
  """Test external keyboard functionality after lock/unlock."""

  def teardown_test(self):
    self.hid.stop_key_capture()
    super().teardown_test()  # pylint: disable=attribute-error

  def test_keyboard_after_lock_unlock(self):
    self.dut.user_tools.lock()
    self.dut.user_tools.unlock()

    logging.info('Starting HID key capture after device is ready')
    self.hid.start_key_capture()

    logging.info('Verifying Top Row (Function) keys after unlock')
    self.verify_all_keys_captured(
        self.emulator,
        [key for key in hid_keys.Function],
    )
    logging.info('Verifying Alphanumeric keys after unlock')
    self.verify_all_keys_captured(
        self.emulator,
        [key for key in hid_keys.Alphanumeric],
    )


if __name__ == '__main__':
  test_runner.main()
