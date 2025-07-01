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

"""Base class for UTC-274 tests that sets tester state between tests."""

from lib.pasit.passport import passport_host
from lib.pasit.passport import passport_usb_service_client as usb
from mobly import base_test
from mobly.controllers import android_device


class UtcBaseTest(base_test.BaseTestClass):
  """Base class for UTC-274 tests.

  This class sets up and resets UTC-274 state between tests.
  It also provides helper methods for checking the displays state.
  """

  passport: passport_host.PassportHost
  utc: usb.PassportUsbServiceClient
  ads: list[android_device.AndroidDevice]
  dut: android_device.AndroidDevice

  def setup_class(self):
    super().setup_class()
    # Setup the UTC-274.
    self.passport = self.register_controller(passport_host)[0]
    self.utc = self.passport.usb_tester_client

    # Open the first detected tester
    testers = self.utc.get_usb_testers()
    self.utc.open_usb_tester(testers.testers[0].id)

    # Set the tester's initial state.
    self._set_usb_tester_default_state()

    # Register android device.
    self.ads = self.register_controller(android_device)
    self.dut = self.ads[0]

  def teardown_test(self):
    # Reset the tester's state.
    self._set_usb_tester_default_state()
    super().teardown_test()

  def teardown_class(self):
    # Teardown the passport host and UTC-274.
    self.passport.teardown()
    super().teardown_class()

  def _set_usb_tester_default_state(self):
    """Sets the USB tester state."""
    self.utc.active_port = 0
    self.utc.pd_init_state = usb.InitPdState.PD_DRP
    self.utc.usb_channel = usb.UsbChannel.USB_3
    self.utc.usb_path = usb.UsbPath.USB_PATH_INTERNAL
    self.utc.cable_mode = usb.CableMode.NORMAL
    self.utc.source_pdo_count = usb.DEFAULT_SRC_PDO_COUNT
    # TODO(b/427189159): Deactive tester port when new API is available.
    self.utc.active_port = 1
    self.utc.replug()
