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
"""Represents keys on a keyboard.

https://www.w3.org/TR/uievents-code/ is the source of truth for the key values.
"""

import enum


class Alphanumeric(enum.StrEnum):
  """Represents an alphanumeric key.

  Contains letter keys, number keys, punctuation keys, space, tab, caps lock.
  """

  # Writing system keys.
  BACKQUOTE = 'Oemtilde'
  BACKSLASH = 'Oem5'
  BRACKET_LEFT = 'OemOpenBrackets'
  BRACKET_RIGHT = 'Oem6'
  COMMA = 'Oemcomma'
  DIGIT_0 = '0'
  DIGIT_1 = '1'
  DIGIT_2 = '2'
  DIGIT_3 = '3'
  DIGIT_4 = '4'
  DIGIT_5 = '5'
  DIGIT_6 = '6'
  DIGIT_7 = '7'
  DIGIT_8 = '8'
  DIGIT_9 = '9'
  EQUAL = 'OemPlus'
  KEY_A = 'A'
  KEY_B = 'B'
  KEY_C = 'C'
  KEY_D = 'D'
  KEY_E = 'E'
  KEY_F = 'F'
  KEY_G = 'G'
  KEY_H = 'H'
  KEY_I = 'I'
  KEY_J = 'J'
  KEY_K = 'K'
  KEY_L = 'L'
  KEY_M = 'M'
  KEY_N = 'N'
  KEY_O = 'O'
  KEY_P = 'P'
  KEY_Q = 'Q'
  KEY_R = 'R'
  KEY_S = 'S'
  KEY_T = 'T'
  KEY_U = 'U'
  KEY_V = 'V'
  KEY_W = 'W'
  KEY_X = 'X'
  KEY_Y = 'Y'
  KEY_Z = 'Z'
  MINUS = 'OemMinus'
  PERIOD = 'OemPeriod'
  QUOTE = 'Oem7'
  SEMICOLON = 'Oem1'
  SLASH = 'OemQuestion'
  # Functional keys.
  ALT_LEFT = 'LMenu'
  ALT_RIGHT = 'RMenu'
  BACKSPACE = 'Back'
  CAPS_LOCK = 'CapsLock'
  CONTROL_LEFT = 'LControl'
  CONTROL_RIGHT = 'RControl'
  ENTER = 'Enter'
  SHIFT_LEFT = 'LShift'
  SHIFT_RIGHT = 'RShift'
  SPACE = 'Space'
  TAB = 'Tab'


class Special(enum.StrEnum):
  """Represents a special key.

  These keys are reserved for special purposes, such as system-level shortcuts.
  They are not interceptable by the key event handler.
  """

  META = 'Meta'
  META_LEFT = 'LMeta'
  META_RIGHT = 'RMeta'
  POWER = 'Power'


class Function(enum.StrEnum):
  """Represents a function key.

  Contains function keys, F1 to F24, F11, F12, and Escape.
  """

  ESCAPE = 'Esc'
  F1 = 'F1'
  F2 = 'F2'
  F3 = 'F3'
  F4 = 'F4'
  F5 = 'F5'
  F6 = 'F6'
  F7 = 'F7'
  F8 = 'F8'
  F9 = 'F9'
  F10 = 'F10'
  F11 = 'F11'
  F12 = 'F12'
  PRINT_SCREEN = 'PrintScreen'
  SCROLL_LOCK = 'ScrollLock'
  PAUSE = 'Pause'


class ArrowPad(enum.StrEnum):
  """Represents an arrow pad.

  Contains arrow keys.
  """

  ARROW_DOWN = 'ArrowDown'
  ARROW_LEFT = 'ArrowLeft'
  ARROW_RIGHT = 'ArrowRight'
  ARROW_UP = 'ArrowUp'


class ControlPad(enum.StrEnum):
  """Represents a control pad.

  Contains page up/down, home, end, insert, delete.
  """

  DELETE = 'Delete'
  END = 'End'
  HOME = 'Home'
  INSERT = 'Insert'
  PAGE_DOWN = 'PageDown'
  PAGE_UP = 'PageUp'


class Numpad(enum.StrEnum):
  """Represents keys on a numeric key pad."""

  NUM_LOCK = 'NumLock'
  NUMPAD_0 = 'NumPad0'
  NUMPAD_1 = 'NumPad1'
  NUMPAD_2 = 'NumPad2'
  NUMPAD_3 = 'NumPad3'
  NUMPAD_4 = 'NumPad4'
  NUMPAD_5 = 'NumPad5'
  NUMPAD_6 = 'NumPad6'
  NUMPAD_7 = 'NumPad7'
  NUMPAD_8 = 'NumPad8'
  NUMPAD_9 = 'NumPad9'
  NUMPAD_ADD = '+'
  NUMPAD_DECIMAL = 'Decimal'
  NUMPAD_DIVIDE = '/'
  NUMPAD_ENTER = 'Return'
  NUMPAD_MULTIPLY = '*'
  NUMPAD_SUBTRACT = '-'


class Media(enum.StrEnum):
  """Represents a Media Key."""

  BROWSER_REFRESH = 'Refresh'
  MEDIA_PLAY_PAUSE = 'MediaPlayPause'
  AUDIO_VOLUME_MUTE = 'AudioVolumeMute'
  MEDIA_TRACK_NEXT = 'MediaTrackNext'
  MEDIA_TRACK_PREVIOUS = 'MediaTrackPrevious'
  AUDIO_VOLUME_UP = 'AudioVolumeUp'
  AUDIO_VOLUME_DOWN = 'AudioVolumeDown'
