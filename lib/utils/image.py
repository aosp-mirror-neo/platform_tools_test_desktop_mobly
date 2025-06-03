"""Utility functions for working with images."""


class Color:
  """Represents a color in RGB with Alpha.

  Attributes:
    r: The red component of the color.
    g: The green component of the color.
    b: The blue component of the color.
    a: The alpha component of the color.
  """

  def __init__(self, r: int, g: int, b: int, a: int):
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

  def __repr__(self):
    return f'Color(r={self.r}, g={self.g}, b={self.b}, a={self.a})'


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
