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

OVEREXPOSED = 'over'
UNDEREXPOSED = 'under'


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
  BLACK = Color(0, 0, 0, 255)


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


def check_rgb_image_matches_color(
    image_raw: bytes, target_color: Color, threshold: float = 0.8
) -> bool:
  """Checks if the color in the image matches the target color using Euclidean distance.

  Args:
    image_raw: The raw image data as bytes.
    target_color: The target color to match against.
    threshold: The similarity threshold (0.0 to 1.0) that determines how strict
      the color matching is. Higher values require closer color matches: - 1.0:
      Requires exact color matches (very strict) - 0.8: Default, allows slight
      variations in color (recommended for most cases) - 0.5: Allows moderate
      color differences - 0.0: Matches any color (effectively disables checking)
      The function counts pixels that meet or exceed this threshold, and returns
      true if enough pixels in the image match the target color.

  Returns:
    True if the color in the image matches the target color above the threshold,
    False otherwise.
  """
  if not (0 <= threshold <= 1):
    raise ValueError('Threshold must be between 0.0 and 1.0')

  # Max possible distance in RGB space is the cube diagonal
  MAX_DISTANCE = math.sqrt(3) * 255

  # Parse image_raw into RGB triplets (assuming 3 bytes per pixel RGB format)
  pixels = [image_raw[i : i + 3] for i in range(0, len(image_raw), 3)]
  total_img_pixels = len(pixels)

  similar_pixels_count = 0

  for pixel in pixels:
    r, g, b = pixel
    distance = color_distance(Color(r, g, b), target_color)
    similarity = 1 - (distance / MAX_DISTANCE)
    similar_pixels_count += bool(similarity >= threshold)

  match_percentage = similar_pixels_count / total_img_pixels
  return match_percentage >= threshold


def is_rgb_image_not_black(image_raw: bytes) -> bool:
  """Checks if the RGB image is not black.

  An image is considered "not black" if it has a sufficient percentage of
  non-black pixels and a variety of color values.

  Args:
    image_raw: The raw image data as bytes.

  Returns:
    True if the image is not black, False otherwise.
  """
  # Values below this are considered "black"
  black_threshold = 10
  # Minimum percentage of non-black pixels to consider active
  minimum_non_black_percent = 5.0
  # Minimum number of unique color values for real content
  minimum_unique_values = 3

  total_pixels = len(image_raw)
  if not image_raw or total_pixels == 0:
    raise ValueError('Image data is empty or not provided.')

  # Count non-black pixels (using a threshold)
  # For most image formats, black is 0 or very close to 0
  non_black = sum(1 for byte in image_raw if byte > black_threshold)
  # Calculate percentage of non-black content
  non_black_percentage = (non_black * 100) / total_pixels

  # Convert samples to a set to eliminate duplicates, then count unique values
  unique_color_count = len(set(image_raw))

  # Screen is showing content if:
  # 1. It has sufficient non-black pixels AND
  # 2. It has enough variety in color values
  return (
      non_black_percentage > minimum_non_black_percent
      and unique_color_count > minimum_unique_values
  )


def process_bmp_img_to_raw(bmp_data: bytes) -> bytes:
  """Processes BMP image data to extract raw RGB pixels.

  Args:
    bmp_data: Raw BMP image data in bytes

  Returns:
    Raw RGB pixel data as bytes

  Raises:
    ValueError: If the BMP format is invalid
  """
  # Validate BMP format
  if not (len(bmp_data) >= 54):
    raise ValueError('Invalid BMP: file too small')
  if bmp_data[0:2] != b'BM':
    raise ValueError('Invalid BMP: missing BMP signature')

  # Extract BMP header information
  bits_per_pixel = int.from_bytes(bmp_data[28:30], byteorder='little')
  compression = int.from_bytes(bmp_data[30:34], byteorder='little')

  if bits_per_pixel != 24:
    raise ValueError(f'Expected 24-bit BMP format, got {bits_per_pixel}-bit')
  if compression != 0:
    raise ValueError(
        f'Only uncompressed BMPs are supported (compression={compression})'
    )

  # Get pixel data offset (location where actual pixel data starts)
  pixel_offset = int.from_bytes(bmp_data[10:14], byteorder='little')
  # Get width and height
  width = int.from_bytes(bmp_data[18:22], byteorder='little')
  height = int.from_bytes(bmp_data[22:26], byteorder='little')

  # Ensure we're actually at pixel data when we think we are
  if pixel_offset >= len(bmp_data):
    raise ValueError(
        f'Pixel data offset ({pixel_offset}) exceeds file size'
        f' ({len(bmp_data)})'
    )

  # Calculate row padding.
  # Each row in a BMP file is padded to be a multiple of 4 bytes.
  # width * 3: Each pixel is 3 bytes (R, G, B for a 24-bit BMP).
  #            This is the number of bytes for the actual pixel data in a row.
  # + 3:       Part of the formula to round up to the nearest multiple of 4.
  # // 4:      Integer division by 4.
  # * 4:       Ensures the stride is a multiple of 4.
  row_stride = ((width * 3 + 3) // 4) * 4

  # Calculate expected file size and verify
  expected_size = pixel_offset + (row_stride * height)
  if len(bmp_data) < expected_size:
    raise ValueError(
        f'BMP file truncated: expected at least {expected_size} bytes, got'
        f' {len(bmp_data)}'
    )

  # Create byte array for raw RGB data
  raw_data = bytearray()

  # Process pixels (BMP stores rows bottom-to-top and pixels in BGR order)
  for y in range(height):
    row_start = pixel_offset + (height - 1 - y) * row_stride
    for x in range(width):
      pixel_pos = row_start + x * 3
      if pixel_pos + 2 >= len(bmp_data):
        continue  # Skip if we're out of bounds

      # Convert BGR to RGB
      b = bmp_data[pixel_pos]
      g = bmp_data[pixel_pos + 1]
      r = bmp_data[pixel_pos + 2]

      # Append RGB values to our raw data
      raw_data.extend([r, g, b])

  return bytes(raw_data)


def color_distance(color1: Color, color2: Color) -> float:
  """Returns the Euclidean distance between two colors."""
  result = math.sqrt(
      (color1.r - color2.r) ** 2
      + (color1.g - color2.g) ** 2
      + (color1.b - color2.b) ** 2
  )
  return result


def binary_search_exposure(
    min_exposure: int,
    max_exposure: int,
    tolerance: int = 100,
    max_iterations: int = 10,
):
  """A stateless binary search generator for determining correct exposure.

  Args:
      min_exposure (int): The minimum possible exposure value.
      max_exposure (int): The maximum possible exposure value.
      tolerance (int): The maximum acceptable range difference between
        min_exposure and max_exposure to consider the search converged (default:
        100).
      max_iterations (int): Maximum iterations to prevent infinite loops
        (default: 10).

  Yields:
      int: The suggested exposure value to test.

  Returns (after None signal or convergence):
      int: The final estimated correct exposure.
  """
  current_min = min_exposure
  current_max = max_exposure
  iteration_count = 0

  while iteration_count < max_iterations:
    # Calculate the midpoint as the next exposure to test
    suggested_exposure = int((current_min + current_max) / 2)

    # Yield the suggested exposure to the caller
    # The caller is expected to provide feedback ('over', 'under', None)
    feedback = yield suggested_exposure
    if feedback == OVEREXPOSED:
      current_max = suggested_exposure
    elif feedback == UNDEREXPOSED:
      current_min = suggested_exposure
    else:
      return 0

    # Check for convergence and return 0 for auto-exposure if
    # we have not found a good exposure yet.
    if abs(current_max - current_min) < tolerance:
      return 0

    iteration_count += 1

  # If max_iterations reached without 'good' or convergence within tolerance
  return 0
