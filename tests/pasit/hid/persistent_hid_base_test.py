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

"""Base class for HID tests where the HID emulator is always plugged in."""

from lib.pasit import pasit_hid
from pasit.hid import hid_base_test


class PersistentHIDBaseTest(hid_base_test.HIDBaseTest):
  """Base class for HID tests where the HID emulator is always plugged in.

  Creates the HID emulator in setup_class and plugs it in.
  Does not unplug the emulator in teardown_class.
  Loads the HID snippet in setup_class and unloads it in teardown_class.
  """

  hid: pasit_hid.PasitHID

  def setup_class(self):
    """Handle the setup for the test."""
    super().setup_class()
    self.hid = self.create(pasit_hid)
    self.plug_in_hid_emulator_and_verify(self.hid)

  def teardown_class(self):
    """Handle the teardown for the class."""
    if hasattr(self, 'hid'):
      self.hid.cleanup()
    super().teardown_class()

  def teardown_test(self):
    # ensure that fixtures are not disabled between tests by not calling the
    # super class teardown_test.
    pass
