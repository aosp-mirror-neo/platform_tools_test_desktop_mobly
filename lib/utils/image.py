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

"""Utility functions for working with images."""

import enum
import math


class Color:
  """Represents a color in RGB with Alpha.

  Attributes:
    r: The red component of the color.
    g: The green component of the color.
    b: The blue component of the color.
    a: The alpha component of the color.
  """

  def __init__(self, r: int, g: int, b: int, a: int = 255):
    self.r = r
    self.g = g
    self.b = b
    self.a = a

  def __eq__(self, other):
    return (
        self.r == other.r
        and self.g == other.g
        and self.b == other.b
        and self.a == other.a
    )

  def __str__(self):
    return f'RGBA({self.r},{self.g},{self.b},{self.a})'

  def __repr__(self):
    """Returns the color as a string in the format AARRGGBB."""
    return f'{self.a:02X}{self.r:02X}{self.g:02X}{self.b:02X}'


class NamedColor(enum.Enum):
  """Predefined colors of Color type.

  Usage:
    NamedColor.RED.value
  """

  RED = Color(255, 0, 0, 255)
  GREEN = Color(0, 255, 0, 255)
  BLUE = Color(0, 0, 255, 255)


def color_diff(color1: Color, color2: Color) -> float:
  """Returns the Euclidean distance between two colors."""
  result = math.sqrt(
      pow(color1.r - color2.r, 2)
      + pow(color1.g - color2.g, 2)
      + pow(color1.b - color2.b, 2)
  )
  return result


class HSV:
  """Represents a color in HSV.

  Attributes:
    hue: The hue component of the color.
    saturation: The saturation component of the color.
    value: The value component of the color.
  """

  def __init__(self, h: float, s: float, v: float):
    self.hue = h
    self.saturation = s
    self.value = v

  def __repr__(self):
    return f'HSV({self.hue},{self.saturation},{self.value})'


class HSVMask:
  """Represents a mask in HSV.

  Attributes:
    min: The minimum HSV value.
    max: The maximum HSV value.
  """

  def __init__(self, min_hsv: HSV, max_hsv: HSV):
    self.min = min_hsv
    self.max = max_hsv
