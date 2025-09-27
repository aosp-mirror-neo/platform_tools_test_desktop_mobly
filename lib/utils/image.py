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
import logging
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
    image_raw: bytes,
    target_color: Color,
    width: int,
    height: int,
    threshold: float = 0.8,
    crop_ratio: float = 1.0,
) -> bool:
  """Checks if the color in the image matches the target color.

  This function can check the entire image or a central cropped region.

  Args:
    image_raw: The raw image data as bytes (RGB format).
    target_color: The target color to match against.
    width: The width of the image.
    height: The height of the image.
    threshold: The similarity threshold (0.0 to 1.0) for a pixel to be
      considered a match. Higher values require closer color matches.
    crop_ratio: The ratio of the image to analyze (from 0.0 to 1.0). A value of
      1.0 checks the entire image. A value of 0.5 checks the central 50% of the
      image, effectively creating a 25% margin on all sides.

  Returns:
    True if the percentage of matching pixels in the analyzed region is at or
    above the threshold, False otherwise.
  """
  if not (0 <= threshold <= 1):
    raise ValueError('Threshold must be between 0.0 and 1.0')
  if not (0.0 <= crop_ratio <= 1.0):
    raise ValueError('crop_ratio must be between 0.0 and 1.0')

  if not image_raw or len(image_raw) != width * height * 3:
    logging.warning(
        'Invalid image data. Expected size %d, got %d.',
        width * height * 3,
        len(image_raw),
    )
    return False

  # Max possible distance in RGB space is the cube diagonal
  MAX_DISTANCE = math.sqrt(3) * 255

  margin_x_ratio = (1.0 - crop_ratio) / 2.0
  margin_y_ratio = (1.0 - crop_ratio) / 2.0

  start_x = int(width * margin_x_ratio)
  end_x = int(width * (1.0 - margin_x_ratio))
  start_y = int(height * margin_y_ratio)
  end_y = int(height * (1.0 - margin_y_ratio))

  total_checked_pixels = (end_x - start_x) * (end_y - start_y)

  if total_checked_pixels == 0:
    return False

  similar_pixels_count = 0
  sum_r, sum_g, sum_b = 0, 0, 0

  for y in range(start_y, end_y):
    for x in range(start_x, end_x):
      pixel_index = (y * width + x) * 3
      r, g, b = (
          image_raw[pixel_index],
          image_raw[pixel_index + 1],
          image_raw[pixel_index + 2],
      )
      sum_r += r
      sum_g += g
      sum_b += b
      distance = color_distance(Color(r, g, b), target_color)
      similarity = 1 - (distance / MAX_DISTANCE)
      similar_pixels_count += bool(similarity >= threshold)

  match_percentage = similar_pixels_count / total_checked_pixels
  result = match_percentage >= threshold

  if not result:
    avg_r = sum_r // total_checked_pixels
    avg_g = sum_g // total_checked_pixels
    avg_b = sum_b // total_checked_pixels
    avg_color = Color(avg_r, avg_g, avg_b)
    logging.info(
        'Color match failed. Match percentage: %.2f, Threshold: %.2f. Target'
        ' color: %s, Average image color: %s',
        match_percentage,
        threshold,
        target_color,
        avg_color,
    )

  return result


def is_rgb_image_not_black(image_raw: bytes) -> bool:
  """Checks if a screen is active by analyzing its raw RGB byte stream.

  This function avoids external libraries. It considers a screen "active"
  if it has a minimum number of pixels that are brighter than a defined
  blackness threshold.

  Args:
    image_raw: The raw RGB image data as a stream of bytes.

  Returns:
    True if the screen is considered active, False otherwise.
  """

  pixel_count = 0
  active_pixel_count = 0
  active_brightness_sum = 0  # sum of brightness of active pixels to calculate average brightness later.
  black_brightness_sum = 0

  def _log_pixel():
    logging.debug(
        f'active pixels: {active_pixel_count} out of {pixel_count}.'
        f' Img size: {len(image_raw)}'
    )
    if active_pixel_count > 0:
      logging.debug(
          f'average brightness: {active_brightness_sum / active_pixel_count}'
      )
    black_pixel_count = pixel_count - active_pixel_count
    if black_pixel_count > 0:
      logging.debug(
          f'black brightness: {black_brightness_sum / black_pixel_count}'
      )

  # Any average brightness value below this is considered "black".
  # This helps ignore minor backlight bleed or sensor noise.
  black_threshold = 10

  # Require at least this many pixels to be "non-black" to confirm a real signal.
  # This filters out single stray pixels or random noise.
  min_active_pixels = 50

  # A valid raw RGB stream should have a length divisible by 3.
  if not image_raw or len(image_raw) % 3 != 0:
    # This could also indicate that the byte stream is not raw RGB data
    # but a file format with a header (like BMP or PNG).
    logging.info(f'Invalid image size: {len(image_raw)}')
    return False

  # Iterate over the data in 3-byte chunks (one pixel at a time).
  for i in range(0, len(image_raw), 3):
    r, g, b = image_raw[i], image_raw[i + 1], image_raw[i + 2]
    pixel_count += 1

    # Calculate the average brightness of the pixel.
    brightness = (r + g + b) // 3

    # Check if the pixel is brighter than our threshold.
    if brightness > black_threshold:
      active_brightness_sum += brightness
      active_pixel_count += 1
      if active_pixel_count >= min_active_pixels:
        _log_pixel()
        return True
    else:
      black_brightness_sum += brightness

  # If the loop completes, not enough active pixels were found.
  _log_pixel()
  return False


def process_bmp_img_to_raw(bmp_data: bytes) -> tuple[bytes, int, int]:
  """Processes BMP image data to extract raw RGB pixels.

  Args:
    bmp_data: Raw BMP image data in bytes

  Returns:
    A tuple containing:
      - Raw RGB pixel data as bytes
      - width of the image
      - height of the image

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
  height = int.from_bytes(bmp_data[22:26], byteorder='little', signed=True)

  # A negative height indicates a top-down bitmap
  is_top_down = height < 0
  if is_top_down:
    height = -height  # Use positive height for calculations

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
    if is_top_down:
      row_start = pixel_offset + y * row_stride
    else:  # Standard bottom-up BMP
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

  return bytes(raw_data), width, height


def color_distance(color1: Color, color2: Color) -> float:
  """Returns the Euclidean distance between two colors."""
  result = math.sqrt(
      (color1.r - color2.r) ** 2
      + (color1.g - color2.g) ** 2
      + (color1.b - color2.b) ** 2
  )
  return result


def get_color_brightness(color: Color) -> int:
  """Returns the average brightness of a color."""
  return (color.r + color.g + color.b) // 3


def get_color_hot_cold(color: Color) -> int:
  """Returns the hotness of a color.

  This is calculated as the difference between the red and blue components.
  A positive value indicates a "hotter" color (more red), while a negative
  value indicates a "colder" color (more blue).

  Args:
    color: The Color object to evaluate.

  Returns:
    An integer representing the red-blue difference.
  """
  return color.r - color.b
