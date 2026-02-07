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

"""A test that exercises PASIT HID emulator functionality."""

import logging

from lib.pasit import hid_emulator
from lib.pasit import hid_keys
from lib.pasit import pasit_hid
from lib.pasit import pasit_test
from mobly import asserts
from mobly import test_runner


class HIDEmulatorTest(pasit_test.PasitTestClass):
  """Test for HID emulator functionality."""

  hid: pasit_hid.PasitHID

  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_HID

  def setup_class(self):
    super().setup_class()
    self.hid = self.create(pasit_hid)

  def test_initialize_before_plug_in_hid_emulator_raises_error(self) -> None:
    emulator = hid_emulator.HIDEmulator(self.passport_host)
    with asserts.assert_raises(hid_emulator.HIDEmulator.Error):
      emulator.initialize()

  def test_keypress_before_initialize_raises_error(self) -> None:
    emulator = hid_emulator.HIDEmulator(self.passport_host)
    with asserts.assert_raises(hid_emulator.HIDEmulator.Error):
      emulator.keypress([hid_keys.Alphanumeric.KEY_A])

  def test_mouse_click_before_initialize_raises_error(self) -> None:
    emulator = hid_emulator.HIDEmulator(self.passport_host)
    with asserts.assert_raises(hid_emulator.HIDEmulator.Error):
      emulator.mouse_click(hid_emulator.MouseButton.LEFT)

  # TODO: b/481006312 - The test is not meeting SLOs and not critical so
  # disabling until we can investigate the issue.
  def disabled_test_plug_unplug_hid_emulator(self) -> None:
    hid_devices_before = self.hid.get_hid_devices()
    self.plug_in_hid_emulator()
    asserts.assert_equal(
        len(self.hid.get_hid_devices()) - len(hid_devices_before),
        3,
        'Expected to find 3 new HIDs after plugging in HID emulator.',
    )

    self.unplug_hid_emulator()
    asserts.assert_equal(
        len(self.hid.get_hid_devices()) - len(hid_devices_before),
        0,
        'Expected to find no new HIDs after unplugging HID emulator.',
    )

  def test_keypress(self) -> None:
    emulator = hid_emulator.HIDEmulator(self.passport_host)
    self.plug_in_hid_emulator()
    emulator.initialize()
    emulator.keypress([hid_keys.Alphanumeric.KEY_A])

    self.unplug_hid_emulator()
    self.plug_in_hid_emulator()
    emulator.initialize()
    emulator.keypress([hid_keys.Alphanumeric.KEY_A])

  def test_mouse_click(self) -> None:
    emulator = hid_emulator.HIDEmulator(self.passport_host)
    self.plug_in_hid_emulator()
    emulator.initialize()
    emulator.mouse_click(hid_emulator.MouseButton.LEFT)

    self.unplug_hid_emulator()
    self.plug_in_hid_emulator()
    emulator.initialize()
    emulator.mouse_click(hid_emulator.MouseButton.RIGHT)

  def plug_in_hid_emulator(self) -> None:
    """Plugs in the HID emulator to the DUT."""
    logging.info('Plugging in HID emulator to DUT')
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_HID)

  def unplug_hid_emulator(self) -> None:
    """Unplugs the HID emulator from the DUT."""
    logging.info('Unplugging HID emulator from DUT')
    self.passport_host.deactivate_device_by_type(self.DEVICE_TYPE_HID)


if __name__ == '__main__':
  test_runner.main()
