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

"""PASIT HID tests that use the HID emulator to send HID events to the DUT."""

import logging

from android.platform.test.annotations import DesktopTest
from lib.pasit import pasit_file
from lib.pasit import pasit_hid
from lib.pasit import test_policy
from lib.utils import retry
from mobly import asserts
from pasit.hid import hid_base_test

KeyboardShortcut = pasit_hid.PasitHID.KeyboardShortcut


@DesktopTest(
    manual=[
        'al_external_input.external_keyboard_p1_keys',
        'al_external_input.external_keyboard_shortcuts',
        'al_external_input.test_all_the_peripherals_connected_to_basic_usb_hub',
    ]
)
class HIDComboKeysTests(hid_base_test.HIDBaseTest):
  """Test for HID functionality."""

  file: pasit_file.PasitFile

  def setup_class(self):
    super().setup_class()
    self.file = self.create(pasit_file)

  def test_combo_keys_screenshot(self) -> None:
    screenshots_before = self._get_screenshots()
    self.emulate_shortcut_combination(KeyboardShortcut.SCREENSHOT)
    new_screenshots = self._wait_for_new_screenshots(screenshots_before)
    asserts.assert_equal(
        len(new_screenshots),
        1,
        'Expected 1 new screenshot from DUT after sending screenshot keys,'
        f' got, new screenshots: {new_screenshots},',
    )

  def test_combo_keys_settings(self) -> None:
    self.emulate_shortcut_combination(KeyboardShortcut.SETTINGS)
    asserts.assert_true(
        self.dut.wait_app_open(self.dut.UiApplication.SETTINGS),
        f'Failed to find the keyboard shortcuts window',
    )
    self.emulate_shortcut_combination(KeyboardShortcut.HOME)
    asserts.assert_true(
        self.dut.wait_app_close(self.dut.UiApplication.SETTINGS),
        f'Failed to close the settings window',
    )

  def emulate_shortcut_combination(self, shortcut: KeyboardShortcut) -> None:
    """Emulates a shortcut combination on the HID emulator."""
    keys = self.hid.get_shortcut_combination(shortcut)
    self.emulator.keypress(keys)

  def _wait_for_new_screenshots(
      self, screenshots_before: list[str]
  ) -> list[str]:
    """Waits for new screenshots to be taken.

    Args:
      screenshots_before: The list of screenshots before the screenshot keys
        were sent to the DUT.

    Returns:
      The list of new screenshots taken after the screenshot keys were sent to
      the DUT.
    """
    logging.debug('Checking for new screenshots')
    screenshots_after = retry.retry(
        self._get_screenshots,
        until=lambda screenshots: len(screenshots) > len(screenshots_before),
        policy=test_policy.HIDTestPolicy.FIND_NEW_SCREENSHOTS_RETRY_POLICY,
    )
    diff = set(screenshots_after) - set(screenshots_before)
    logging.debug('Screenshots after: %s', screenshots_after)
    return list(diff)

  def _get_screenshots(self) -> list[str]:
    """Returns the list of screenshots on the DUT.

    If the screenshots directory does not exist, returns an empty list.
    """
    try:
      return self.file.list_files(self.dut.get_screenshots_path())
    except FileNotFoundError:
      return []
