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

import logging
import os
import sys
from typing import List, TypeAlias

from lib.pasit import hid_emulator
from lib.pasit import hid_keys
from lib.pasit.android import android_ui_tools
from lib.pasit.base import base_pasit_hid
from mobly.controllers import android_device
from mobly.controllers.android_device_lib import apk_utils


PasitHIDError: TypeAlias = base_pasit_hid.BasePasitHID.Error
KeyboardShortcut: TypeAlias = base_pasit_hid.BasePasitHID.KeyboardShortcut
MouseAction: TypeAlias = base_pasit_hid.BasePasitHID.MouseAction
MouseButton: TypeAlias = base_pasit_hid.BasePasitHID.MouseButton


_CAPTURED_EVENT_DOWN_PREFIX = 'DOWN: '
_CAPTURED_EVENT_UP_PREFIX = 'UP: '

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
    # Media
    hid_keys.Media.MEDIA_PLAY_PAUSE: ['KEYCODE_MEDIA_PLAY_PAUSE'],
    hid_keys.Media.AUDIO_VOLUME_MUTE: ['KEYCODE_VOLUME_MUTE'],
    hid_keys.Media.MEDIA_TRACK_NEXT: ['KEYCODE_MEDIA_NEXT'],
    hid_keys.Media.MEDIA_TRACK_PREVIOUS: ['KEYCODE_MEDIA_PREVIOUS'],
    hid_keys.Media.AUDIO_VOLUME_UP: ['KEYCODE_VOLUME_UP'],
    hid_keys.Media.AUDIO_VOLUME_DOWN: ['KEYCODE_VOLUME_DOWN'],
}

_OVERRIDE_CAPTURED_MOUSE_EVENTS_MAP = {
    MouseButton.LEFT: 'PRIMARY',
    MouseButton.RIGHT: 'SECONDARY',
    MouseButton.MIDDLE: 'TERTIARY',
    MouseButton.BACK: 'BACK',
    MouseButton.FORWARD: 'KEYCODE_FORWARD',
}


class AndroidPasitHID(base_pasit_hid.BasePasitHID):
  """PasitHID for Android devices."""

  _HID_SNIPPET_APK_PATH = os.path.join(
      os.path.dirname(os.path.abspath(sys.argv[0])),
      'HidDeviceSnippet.apk',
  )

  def __init__(self, controller: android_device.AndroidDevice):
    """Initializes the AndroidPasitHID."""
    super().__init__(controller)
    self.ui_tools = android_ui_tools.AndroidUITools(self.controller)
    self.package_name = self.ui_tools.get_app_package_name(
        android_ui_tools.AndroidUIApplication.HID_SNIPPET
    )
    # uninstall apks to avoid INSTALL_FAILED_UPDATE_INCOMPATIBLE errors
    apk_utils.uninstall(
        self.controller,
        self.package_name,
    )
    apk_utils.install(
        self.controller,
        self._HID_SNIPPET_APK_PATH,
    )
    self.controller.load_snippet('hid', self.package_name)

  def cleanup(self):
    """Cleans up after testing.

    Uninstalls the HidDeviceSnippet when the object is garbage collected.
    """
    self.controller.unload_snippet('hid')
    apk_utils.uninstall(self.controller, self.package_name)

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
      case KeyboardShortcut.SCREENSHOT:
        return [hid_keys.Special.META, hid_keys.Alphanumeric.KEY_S]
      case KeyboardShortcut.SETTINGS:
        return [hid_keys.Special.META, hid_keys.Alphanumeric.KEY_I]
      case KeyboardShortcut.HOME:
        return [hid_keys.Special.META, hid_keys.Alphanumeric.KEY_H]
      case _:
        raise ValueError(f'Unsupported shortcut: {shortcut}')

  def start_key_capture(self) -> None:
    self._start_capture_activity()

  def stop_key_capture(self) -> None:
    self._stop_capture_activity()

  def get_captured_key_events(self) -> List[str]:
    return self.controller.hid.getKeyLog()

  def get_expected_key_events(self, key: str) -> List[str]:
    if key in _OVERRIDE_CAPTURED_KEY_EVENTS_MAP.keys():
      return self._get_key_events_set(_OVERRIDE_CAPTURED_KEY_EVENTS_MAP[key])
    else:
      return self._get_key_events_set([f'KEYCODE_{key.upper()}'])

  def start_mouse_capture(self, emulator: hid_emulator.HIDEmulator) -> None:
    self._enable_pointer_location(True)
    self._start_capture_activity()
    self._move_mouse_to_window(emulator)
    self.controller.hid.clearLogs()

  def stop_mouse_capture(self) -> None:
    self._stop_capture_activity()
    self._enable_pointer_location(False)

  def get_captured_mouse_events(self) -> List[str]:
    return self.controller.hid.getMouseLog()

  def get_expected_mouse_events(
      self, action: MouseAction, button: MouseButton | None = None
  ) -> List[str]:
    match action:
      case MouseAction.MOVE:
        return ['ACTION_HOVER_MOVE']
      case MouseAction.CLICK:
        if button is None:
          raise ValueError(
              'A mouse button must be provided for the CLICK action.'
          )
        return self._get_mouse_events_set(button)
      case MouseAction.SCROLL:
        return ['ACTION_SCROLL']
      case _:
        raise ValueError(f'Unsupported action: {action}')

  def _get_key_events_set(self, keys: List[str]) -> List[str]:
    """Returns the key events for the given key."""
    return [_CAPTURED_EVENT_DOWN_PREFIX + key for key in keys] + [
        _CAPTURED_EVENT_UP_PREFIX + key for key in keys
    ]

  def _get_mouse_events_set(self, button: MouseButton) -> List[str]:
    """Returns the mouse events for the given mouse buttons."""
    mouse_event = _OVERRIDE_CAPTURED_MOUSE_EVENTS_MAP[button]
    return [_CAPTURED_EVENT_DOWN_PREFIX + mouse_event] + [
        _CAPTURED_EVENT_UP_PREFIX
        + (
            # CaptureActivity logs "UNKNOWN" for most button release events,
            # except for the BACK and FORWARD buttons.
            mouse_event
            if button in [MouseButton.BACK, MouseButton.FORWARD]
            else 'UNKNOWN'
        )
    ]

  def _start_capture_activity(self) -> None:
    """Starts the capture activity using the Mobly snippet."""
    self.controller.hid.startCaptureActivity()
    self.ui_tools.wait_app_open(
        android_ui_tools.AndroidUIApplication.HID_SNIPPET
    )
    self.ui_tools.maximize_app_window(
        android_ui_tools.AndroidUIApplication.HID_SNIPPET
    )

  def _stop_capture_activity(self) -> None:
    """Stops the capture activity using the Mobly snippet."""
    self.controller.hid.stopCaptureActivity()
    self.ui_tools.wait_app_close(
        android_ui_tools.AndroidUIApplication.HID_SNIPPET
    )

  def _enable_pointer_location(self, enable: bool) -> None:
    """Enables or disables the 'Pointer location' developer option via adb.

    This setting overlays crosshairs and coordinates on the screen for touch
    and mouse events, which is helpful for visually debugging pointer inputs.

    Args:
      enable: Whether to enable or disable the 'Pointer location' developer
        option.
    """
    self.controller.adb.shell([
        'settings',
        'put',
        'system',
        'pointer_location',
        '1' if enable else '0',
    ])

  def _move_mouse_to_window(self, emulator: hid_emulator.HIDEmulator) -> None:
    """Moves the mouse to the zero position."""
    # Move the mouse to the top left corner of the screen.
    emulator.mouse_move(
        -int(self.controller.ui.width), -int(self.controller.ui.height)
    )
    # Move the mouse down and right. The values passed to mouse_move do not
    # correspond one-to-one with actual screen pixels, making it tricky to
    # accurately target the center of the screen. However, since the HID Capture
    # window is maximized, an offset of 200 is a good enough estimate to safely
    # place the cursor inside the window while avoiding system edge gestures
    # and status bars.
    emulator.mouse_move(200, 200)
