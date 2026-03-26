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

"""A base class for PASIT HID tests."""

from lib.pasit import hid_emulator
from lib.pasit import hid_helper
from lib.pasit import pasit_hid
from lib.pasit import pasit_test


class PasitHIDBaseTest(pasit_test.PasitTestClass):
  """A base class for PASIT HID tests."""

  hid: pasit_hid.PasitHID
  emulator: hid_emulator.HIDEmulator
  helper: hid_helper.HIDHelper

  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_HID

  def setup_class(self):
    super().setup_class()
    self.hid = self.create(pasit_hid)
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_HID)
    self.emulator = hid_emulator.HIDEmulator(self.passport_host)
    self.helper = hid_helper.HIDHelper(self.emulator)
    self.helper.initialize_hid_emulator()
    self.helper.wait_for_hid_connected(self.hid)

  def teardown_test(self):
    """Handle the teardown for the test."""
    # TODO: b/496256429 - avoid passport reset in PasitTestClass.teardown_test
    # to keep the HID plugged in until teardown_class.
    # super().teardown_test()
