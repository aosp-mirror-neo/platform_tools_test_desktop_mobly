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

from lib.pasit import pasit_file
from lib.pasit import pasit_hid
from lib.pasit import pasit_test
from mobly import asserts
from mobly import signals


class HIDBaseTest(pasit_test.PasitTestClass):
  """Test for HID functionality."""

  file_interface: pasit_file.PasitFile
  hid_device: str | None = None
  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_HID

  def setup_class(self):
    """Handle the setup for the test."""
    super().setup_class()
    self.file_interface = self.create(pasit_file)
    self.hid = self.create(pasit_hid)
    default_hid_devices = self.hid.get_hid_devices()
    # Initialize HID once before all tests. HID must be connected to the DUT
    # before initialization to provide power to HID emulator.
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_HID)
    # After activation, HID devices should be visible to passport
    hid_devices = self.passport_host.hid_client.get_hid_devices()
    logging.info('Passport HID devices: %s', hid_devices)
    if len(hid_devices) != 1:
      raise signals.TestError(
          'Expected 1 HID device connected to the Passport host, but found'
          f' {len(hid_devices)} devices. Check your testbed configuration to'
          ' ensure only one and only one HID device is connected to the'
          ' Passport host.'
      )
    self.hid_device = hid_devices[0]
    self.passport_host.hid_client.open(self.hid_device)

    # after activation the HID devices should be visible to the DUT
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
    if self.hid_device:
      self.passport_host.hid_client.close(self.hid_device)
    self.hid.cleanup()
    super().teardown_class()

  def teardown_test(self):
    # ensure that switches are not disabled between tests by not calling the
    # super class teardown_test.
    pass
