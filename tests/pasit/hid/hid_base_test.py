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

"""Base class for HID tests."""

import logging

from lib.pasit import hid_emulator
from lib.pasit import pasit_hid
from lib.pasit import pasit_test
from mobly import asserts


class HIDBaseTest(pasit_test.PasitTestClass):
  """Test for HID functionality."""

  hid: pasit_hid.PasitHID
  emulator: hid_emulator.HIDEmulator

  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_HID

  def setup_class(self):
    """Handle the setup for the test."""
    super().setup_class()
    self.hid = self.create(pasit_hid)
    default_hid_devices = self.hid.get_hid_devices()

    self.plug_in_hid_emulator()
    self.emulator = hid_emulator.HIDEmulator(self.passport_host)
    self.emulator.initialize()

    self._verify_hid_emulator_is_visible_to_dut(default_hid_devices)

  def _verify_hid_emulator_is_visible_to_dut(
      self, default_hid_devices: list[str]
  ) -> None:
    updated_hid_devices = self.hid.get_hid_devices()
    new_hid_devices = [
        dev for dev in updated_hid_devices if dev not in default_hid_devices
    ]
    logging.info('New HID devices seen by DUT: %s', new_hid_devices)
    asserts.assert_equal(
        len(new_hid_devices),
        3,
        'Expected DUT to have 3 new HID devices after activation of HID'
        ' emulator.',
    )

  def teardown_class(self):
    """Handle the teardown for the class."""
    if hasattr(self, 'hid'):
      self.hid.cleanup()
    super().teardown_class()

  def teardown_test(self):
    # ensure that switches are not disabled between tests by not calling the
    # super class teardown_test.
    pass

  def plug_in_hid_emulator(self) -> None:
    """Plugs in the HID emulator to the DUT."""
    logging.info('Plugging in HID emulator to DUT')
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_HID)
