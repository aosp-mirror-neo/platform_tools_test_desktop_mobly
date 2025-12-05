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

"""AndroidPasitHID handles HID operations for PASIT testing on Android devices."""

import datetime
import logging
import os
import sys
from typing import List

from lib.pasit import hid_keys
from lib.pasit.base import base_pasit_hid
from mobly.controllers import android_device
from mobly.controllers.android_device_lib import apk_utils

PasitHIDError = base_pasit_hid.BasePasitHID.Error

_CAPTURED_KEY_EVENT_DOWN_PREFIX = 'DOWN: '
_CAPTURED_KEY_EVENT_UP_PREFIX = 'UP: '

_OVERRIDE_CAPTURED_KEY_EVENTS_MAP = {
    # Alphanumeric
    hid_keys.Alphanumeric.BACKQUOTE: ['KEYCODE_GRAVE'],
    hid_keys.Alphanumeric.BACKSLASH: ['KEYCODE_BACKSLASH'],
    hid_keys.Alphanumeric.BRACKET_LEFT: ['KEYCODE_LEFT_BRACKET'],
    hid_keys.Alphanumeric.BRACKET_RIGHT: ['KEYCODE_RIGHT_BRACKET'],
    hid_keys.Alphanumeric.COMMA: ['KEYCODE_COMMA'],
    hid_keys.Alphanumeric.EQUAL: ['KEYCODE_EQUALS'],
    hid_keys.Alphanumeric.MINUS: ['KEYCODE_MINUS'],
    hid_keys.Alphanumeric.PERIOD: ['KEYCODE_PERIOD'],
    hid_keys.Alphanumeric.QUOTE: ['KEYCODE_APOSTROPHE'],
    hid_keys.Alphanumeric.SEMICOLON: ['KEYCODE_SEMICOLON'],
    hid_keys.Alphanumeric.SLASH: ['KEYCODE_SLASH'],
    hid_keys.Alphanumeric.BACKSPACE: ['KEYCODE_DEL'],
    hid_keys.Alphanumeric.CAPS_LOCK: ['KEYCODE_CAPS_LOCK'],
    hid_keys.Alphanumeric.ALT_LEFT: ['KEYCODE_ALT_LEFT'],
    hid_keys.Alphanumeric.ALT_RIGHT: ['KEYCODE_ALT_RIGHT'],
    hid_keys.Alphanumeric.CONTROL_LEFT: ['KEYCODE_CTRL_LEFT'],
    hid_keys.Alphanumeric.CONTROL_RIGHT: ['KEYCODE_CTRL_RIGHT'],
    hid_keys.Alphanumeric.SHIFT_LEFT: ['KEYCODE_SHIFT_LEFT'],
    hid_keys.Alphanumeric.SHIFT_RIGHT: ['KEYCODE_SHIFT_RIGHT'],
    # Function
    hid_keys.Function.ESCAPE: ['KEYCODE_ESCAPE'],
    hid_keys.Function.PRINT_SCREEN: ['KEYCODE_SYSRQ'],
    hid_keys.Function.SCROLL_LOCK: ['KEYCODE_SCROLL_LOCK'],
    hid_keys.Function.PAUSE: ['KEYCODE_BREAK'],
    # Arrow pad
    hid_keys.ArrowPad.ARROW_DOWN: ['KEYCODE_DPAD_DOWN'],
    hid_keys.ArrowPad.ARROW_LEFT: ['KEYCODE_DPAD_LEFT'],
    hid_keys.ArrowPad.ARROW_RIGHT: ['KEYCODE_DPAD_RIGHT'],
    hid_keys.ArrowPad.ARROW_UP: ['KEYCODE_DPAD_UP'],
    # Control pad
    hid_keys.ControlPad.DELETE: ['KEYCODE_FORWARD_DEL'],
    hid_keys.ControlPad.END: ['KEYCODE_MOVE_END'],
    hid_keys.ControlPad.HOME: ['KEYCODE_MOVE_HOME'],
    hid_keys.ControlPad.PAGE_DOWN: ['KEYCODE_PAGE_DOWN'],
    hid_keys.ControlPad.PAGE_UP: ['KEYCODE_PAGE_UP'],
    # Numpad
    hid_keys.Numpad.NUM_LOCK: ['KEYCODE_NUM_LOCK'],
    hid_keys.Numpad.NUMPAD_0: ['KEYCODE_NUMPAD_0'],
    hid_keys.Numpad.NUMPAD_1: ['KEYCODE_NUMPAD_1'],
    hid_keys.Numpad.NUMPAD_2: ['KEYCODE_NUMPAD_2'],
    hid_keys.Numpad.NUMPAD_3: ['KEYCODE_NUMPAD_3'],
    hid_keys.Numpad.NUMPAD_4: ['KEYCODE_NUMPAD_4'],
    hid_keys.Numpad.NUMPAD_5: ['KEYCODE_NUMPAD_5'],
    hid_keys.Numpad.NUMPAD_6: ['KEYCODE_NUMPAD_6'],
    hid_keys.Numpad.NUMPAD_7: ['KEYCODE_NUMPAD_7'],
    hid_keys.Numpad.NUMPAD_8: ['KEYCODE_NUMPAD_8'],
    hid_keys.Numpad.NUMPAD_9: ['KEYCODE_NUMPAD_9'],
    hid_keys.Numpad.NUMPAD_ADD: ['KEYCODE_NUMPAD_ADD'],
    hid_keys.Numpad.NUMPAD_DECIMAL: ['KEYCODE_NUMPAD_DOT'],
    hid_keys.Numpad.NUMPAD_DIVIDE: ['KEYCODE_NUMPAD_DIVIDE'],
    hid_keys.Numpad.NUMPAD_ENTER: ['KEYCODE_NUMPAD_ENTER'],
    hid_keys.Numpad.NUMPAD_MULTIPLY: ['KEYCODE_NUMPAD_MULTIPLY'],
    hid_keys.Numpad.NUMPAD_SUBTRACT: ['KEYCODE_NUMPAD_SUBTRACT'],
}


class AndroidPasitHID(base_pasit_hid.BasePasitHID):
  """PasitHID for Android devices."""

  KeyboardShortcut = base_pasit_hid.BasePasitHID.KeyboardShortcut

  _HID_SNIPPET_PACKAGE_NAME = 'com.google.android.hiddevicesnippet'
  _HID_SNIPPET_APK_PATH = os.path.join(
      os.path.dirname(os.path.abspath(sys.argv[0])),
      'HidDeviceSnippet.apk',
  )

  def __init__(self, controller: android_device.AndroidDevice):
    """Initializes the AndroidPasitHID."""
    super().__init__(controller)
    # uninstall apks to avoid INSTALL_FAILED_UPDATE_INCOMPATIBLE errors
    apk_utils.uninstall(self.controller, self._HID_SNIPPET_PACKAGE_NAME)
    apk_utils.install(
        self.controller,
        self._HID_SNIPPET_APK_PATH,
    )
    self.controller.load_snippet('hid', self._HID_SNIPPET_PACKAGE_NAME)

  def cleanup(self):
    """Cleans up after testing.

    Uninstalls the HidDeviceSnippet when the object is garbage collected.
    """
    self.controller.unload_snippet('hid')
    apk_utils.uninstall(self.controller, self._HID_SNIPPET_PACKAGE_NAME)

  def get_hid_devices(self) -> List[base_pasit_hid.BasePasitHID.DeviceInfo]:
    """Returns a list of connected HID devices using the Mobly snippet."""
    try:
      devices_json = self.controller.hid.getHidDevices()
    except Exception as e:  # pylint: disable=broad-except
      raise PasitHIDError('Failed to get HID devices') from e
    # The snippet returns a list of dictionaries.
    # Convert each dictionary to our HidDeviceInfo dataclass.
    hid_devices = [
        base_pasit_hid.BasePasitHID.DeviceInfo(
            name=device_info['name'],
            vendor_id=device_info['vendorId'],
            product_id=device_info['productId'],
            type=device_info['type'],
        )
        for device_info in devices_json
    ]
    logging.debug('HID devices: %s', hid_devices)
    return hid_devices

  def get_shortcut_combination(self, shortcut: KeyboardShortcut) -> List[str]:
    match shortcut:
      case self.KeyboardShortcut.SCREENSHOT:
        return [hid_keys.Special.META, hid_keys.Alphanumeric.KEY_S]
      case self.KeyboardShortcut.SETTINGS:
        return [hid_keys.Special.META, hid_keys.Alphanumeric.KEY_I]
      case self.KeyboardShortcut.HOME:
        return [hid_keys.Special.META, hid_keys.Alphanumeric.KEY_H]
      case _:
        raise ValueError(f'Unsupported shortcut: {shortcut}')

  def start_key_capture(self) -> None:
    """Starts the key capture activity using the Mobly snippet."""
    self.controller.hid.startKeyCaptureActivity()
    self.controller.ui(pkg=self._HID_SNIPPET_PACKAGE_NAME).wait.exists(
        timeout=datetime.timedelta(seconds=5)
    )

  def stop_key_capture(self) -> None:
    """Stops the key capture activity using the Mobly snippet."""
    self.controller.hid.stopKeyCaptureActivity()
    self.controller.ui(pkg=self._HID_SNIPPET_PACKAGE_NAME).wait.gone(
        timeout=datetime.timedelta(seconds=5)
    )

  def get_captured_key_events(self) -> List[str]:
    return self.controller.hid.getKeyLog()

  def get_expected_key_events(self, key: str) -> List[str]:
    """Returns the expected key events for the given key."""
    if key in _OVERRIDE_CAPTURED_KEY_EVENTS_MAP.keys():
      return self._get_key_events_set(_OVERRIDE_CAPTURED_KEY_EVENTS_MAP[key])
    else:
      return self._get_key_events_set([f'KEYCODE_{key.upper()}'])

  def _get_key_events_set(self, keys: List[str]) -> List[str]:
    """Returns the key events for the given key."""
    return [_CAPTURED_KEY_EVENT_DOWN_PREFIX + key for key in keys] + [
        _CAPTURED_KEY_EVENT_UP_PREFIX + key for key in keys
    ]
