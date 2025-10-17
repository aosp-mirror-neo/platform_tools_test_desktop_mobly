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

from collections.abc import Iterable
import logging

from android.platform.test.annotations import DesktopTest
from lib.pasit import pasit_file
from lib.pasit import test_policy
from lib.utils import retry
from mobly import asserts
from pasit.hid import hid_base_test


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
    screenshot_keys = self.hid.get_shortcut_combination(
        self.hid.KeyboardShortcut.SCREENSHOT
    )
    screenshots_before = self.get_screenshots()
    logging.info('Sending screenshot keys to DUT: %s', screenshot_keys)
    self.passport_host.hid_client.send_keypress(
        self.hid_device, screenshot_keys
    )

    logging.debug('Checking for new screenshots')
    new_screenshots = retry.retry(
        lambda: self._get_new_screenshots(screenshots_before),
        until=lambda new_screenshots: new_screenshots,
        policy=test_policy.HIDTestPolicy.FIND_NEW_SCREENSHOTS_RETRY_POLICY,
    )
    asserts.assert_equal(
        len(new_screenshots),
        1,
        'Expected 1 new screenshot from DUT after sending screenshot keys,'
        f' got, new screenshots: {new_screenshots},',
    )

  def _get_new_screenshots(
      self, screenshots_before: list[str]
  ) -> Iterable[str]:
    screenshots_after = self.get_screenshots()
    # diff the screenshots to ensure that a new screenshot was taken
    diff = set(screenshots_after) - set(screenshots_before)
    logging.debug('Screenshots after: %s', screenshots_after)
    return diff

  def test_combo_keys_settings(self) -> None:
    show_settings_keys = self.hid.get_shortcut_combination(
        self.hid.KeyboardShortcut.SETTINGS
    )
    home_keys = self.hid.get_shortcut_combination(
        self.hid.KeyboardShortcut.HOME
    )
    self.passport_host.hid_client.send_keypress(
        self.hid_device, show_settings_keys
    )
    asserts.assert_true(
        self.dut.wait_app_open(self.dut.UiApplication.SETTINGS),
        f'Failed to find the keyboard shortcuts window',
    )
    self.passport_host.hid_client.send_keypress(self.hid_device, home_keys)
    asserts.assert_true(
        self.dut.wait_app_close(self.dut.UiApplication.SETTINGS),
        f'Failed to close the settings window',
    )

  def get_screenshots(self) -> list[str]:
    """Returns the list of screenshots on the DUT.

    If the screenshots directory does not exist, returns an empty list.
    """
    try:
      return self.file.list_files(self.dut.get_screenshots_path())
    except FileNotFoundError:
      return []
