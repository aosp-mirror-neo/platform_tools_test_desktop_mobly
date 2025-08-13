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

"""Helper class for capturing colors from a camera."""

import enum
import logging

from lib.pasit.passport import passport_host
from lib.utils import image


class ExposureFeedback(enum.StrEnum):
  """Enum for the feedback from an exposure test."""

  OVEREXPOSED = 'over'
  UNDEREXPOSED = 'under'
  BALANCED = 'balanced'


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
  """
  current_min = min_exposure
  current_max = max_exposure
  iteration_count = 0

  while iteration_count < max_iterations:
    # Calculate the midpoint as the next exposure to test
    suggested_exposure = int((current_min + current_max) / 2)

    # Yield the suggested exposure to the caller.
    # The caller is expected to provide ExposureFeedback
    feedback = yield suggested_exposure
    match feedback:
      case ExposureFeedback.OVEREXPOSED:
        current_max = suggested_exposure
      case ExposureFeedback.UNDEREXPOSED:
        current_min = suggested_exposure
      case ExposureFeedback.BALANCED:
        # stop the search
        return
      case _:
        raise ValueError(f'Invalid feedback: {feedback}')

    # Check for convergence and yield 0 for auto-exposure if
    # we have not found a good exposure yet.
    if abs(current_max - current_min) < tolerance:
      # min and max have converged, so break out of the loop.
      break

    iteration_count += 1

  # If we have not found a good exposure yet, yield 0 for auto-exposure.
  yield 0
  return


class MatchedColorIterator:
  """Iterator for captured colors from a camera.

  This iterator uses a binary search to find the exposure time for the camera to
  properly capture the color on the display.

  Attributes:
    passport: The passport host to send the HSV analysis request to.
    camera_id: The camera ID to use for the HSV analysis.
    log_path: The log path for debug logs.
    camera_capture_prefix: The prefix to use for the camera capture.
    exposure_times_generator: The generator for exposure times.
    exposure_feedback: The exposure feedback from the last HSV match info.

    Yields:
      The matched color from the camera capture.
  """

  # The minimum percentage of pixels that must match for a color to be
  # considered a match, we set this to a low value because glare on the display
  # can cause a lot of pixels to be washed out and close to white rather than
  # the expected color.
  _MATCH_PERCENTAGE_THRESHOLD = 40.0

  # HSV masks for PASIT displays. +/-30 degrees from the expected color gives
  # reasonable results, with the exception of green which has more on the plus
  # end to make it pass on sample set of images in passport unit tests.
  _HSV_MASKS_PASIT = {
      image.NamedColor.RED.name: image.HSVMask(
          image.HSV(h=330, s=0.45, v=0.55),
          image.HSV(h=30, s=1.0, v=1.0),
      ),
      image.NamedColor.GREEN.name: image.HSVMask(
          image.HSV(h=90, s=0.45, v=0.55),
          image.HSV(h=165, s=1.0, v=1.0),
      ),
      image.NamedColor.BLUE.name: image.HSVMask(
          image.HSV(h=210, s=0.45, v=0.55),
          image.HSV(h=270, s=1.0, v=1.0),
      ),
      image.NamedColor.BLACK.name: image.HSVMask(
          image.HSV(h=0, s=0, v=0),
          image.HSV(h=360, s=1.0, v=0.6),
      ),
      ExposureFeedback.UNDEREXPOSED: image.HSVMask(
          image.HSV(h=0, s=0, v=0),
          image.HSV(h=360, s=1.0, v=0.5),
      ),
      ExposureFeedback.OVEREXPOSED: image.HSVMask(
          image.HSV(h=0, s=0, v=0.85),
          image.HSV(h=360, s=1.0, v=1.0),
      ),
  }

  def __init__(
      self,
      passport: passport_host.PassportHost,
      camera_id: str,
      log_path: str,
      min_exposure: int,
      max_exposure: int,
      camera_capture_prefix: str = '',
  ):
    """Initializes the exposure time iterator.

    Args:
      passport: The passport host to send the HSV analysis request to.
      camera_id: The camera ID to use for the HSV analysis.
      log_path: The log path for debug logs.
      min_exposure: The minimum exposure time in microseconds.
      max_exposure: The maximum exposure time in microseconds.
      camera_capture_prefix: The prefix to use for the camera capture.
    """
    self.passport = passport
    self.camera_id = camera_id
    self.log_path = log_path
    self.camera_capture_prefix = camera_capture_prefix

    self.exposure_times_generator = binary_search_exposure(
        min_exposure=min_exposure, max_exposure=max_exposure
    )
    self.exposure_feedback = None

  def __iter__(self):
    return self

  def __next__(self):
    """Returns the next matched color."""
    exposure_time_us = self.exposure_times_generator.send(
        self.exposure_feedback
    )
    hsv_match_info = self._get_hsv_match_info(exposure_time_us)
    self.exposure_feedback = self._get_exposure_feedback(hsv_match_info)
    logging.debug(f'Exposure feedback: {self.exposure_feedback}')
    return self._get_matched_color(hsv_match_info)

  def _get_hsv_match_info(
      self,
      exposure_time_us: int,
  ) -> dict[str, float]:
    """Returns the HSV match info from the HSV analysis."""
    logging.debug(f'Camera {self.camera_id} Exposure time: {exposure_time_us}')
    hsv_match_info = self.passport.analyze_hsv(
        self.camera_id,
        self._HSV_MASKS_PASIT,
        self.log_path,
        f'{self.camera_capture_prefix}{self.camera_id}_{exposure_time_us}'
        if self.camera_capture_prefix
        else '',
        exposure_time_us=exposure_time_us,
    )
    logging.debug('HSV match percentages: %s', hsv_match_info)
    return hsv_match_info

  def _get_matched_color(
      self,
      hsv_match_percentages: dict[str, float],
  ) -> image.NamedColor | None:
    """Finds the matched color from the HSV match percentages.

    Args:
      hsv_match_percentages: The HSV match percentages from the HSV analysis.

    Returns:
      The matched color from the HSV match percentages, or None if no color is
      matched.
    """
    # handle the case where are hsv percentage values are 0 since protobuf
    # optimizes out the 0 values we end up with an empty dict.
    if not hsv_match_percentages:
      return None
    match_color = max(
        hsv_match_percentages,
        key=hsv_match_percentages.get,
    )
    match_percentage = hsv_match_percentages[match_color]
    if match_percentage < self._MATCH_PERCENTAGE_THRESHOLD:
      logging.debug(
          'Did not match any color, max match percentage is %s:%.2f',
          match_color,
          match_percentage,
      )
      return None
    try:
      return image.NamedColor[match_color]
    except KeyError:
      return None

  def _get_exposure_feedback(
      self, hsv_match_info: dict[str, float]
  ) -> ExposureFeedback:
    """Returns the exposure feedback from the HSV match info."""
    exposure_feedback_info = {
        key: value
        for key, value in hsv_match_info.items()
        if key in [e.value for e in ExposureFeedback]
    }
    return (
        ExposureFeedback(
            max(exposure_feedback_info.items(), key=lambda x: x[1])[0]
        )
        if exposure_feedback_info
        else ExposureFeedback.BALANCED
    )
