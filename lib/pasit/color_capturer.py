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


_EXPOSURE_FEEDBACK_MASKS = {
    ExposureFeedback.UNDEREXPOSED.value: image.HSVMask(
        image.HSV(h=0, s=0, v=0),
        image.HSV(h=360, s=1.0, v=0.5),
    ),
    ExposureFeedback.OVEREXPOSED.value: image.HSVMask(
        image.HSV(h=0, s=0, v=0.85),
        image.HSV(h=360, s=1.0, v=1.0),
    ),
}


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


class ExposureStabilityTracker:
  """Tracks exposure stability over multiple samples.

  Considers the exposure stable if the last N samples are all within the
  threshold.
  """

  _STABILITY_THRESHOLD = 2.0
  _STABILITY_COUNT = 3
  _BALANCED_THRESHOLD = 20.0

  def __init__(self):
    self._history = []

  def add_sample(self, hsv_match_info: dict[str, float]) -> None:
    """Adds a sample to the tracker."""
    self._history.append(hsv_match_info)
    if len(self._history) > self._STABILITY_COUNT:
      self._history.pop(0)

  def _is_stable(self, prev: dict[str, float], curr: dict[str, float]) -> bool:
    """Checks if the samples are within the stability thresholds."""
    all_keys = set(prev.keys()) | set(curr.keys())
    exposure_keys = [
        key for key in all_keys if key in {e.value for e in ExposureFeedback}
    ]
    for key in exposure_keys:
      diff = abs(curr.get(key, 0.0) - prev.get(key, 0.0))
      if diff >= self._STABILITY_THRESHOLD:
        return False
    return True

  def get_feedback(self) -> ExposureFeedback:
    """Returns the exposure feedback based on stability."""
    if len(self._history) < self._STABILITY_COUNT:
      return self._get_directional_feedback()

    # Check stability across all masks
    is_stable = True
    for i in range(1, len(self._history)):
      prev = self._history[i - 1]
      curr = self._history[i]
      is_stable = self._is_stable(prev, curr)
      if not is_stable:
        break

    if is_stable:
      latest = self._history[-1]
      over_percentage = latest.get(ExposureFeedback.OVEREXPOSED.value, 0.0)
      under_percentage = latest.get(ExposureFeedback.UNDEREXPOSED.value, 0.0)
      # Prevent maxed out over or under exposure from being considered balanced
      # and causing the exposure search to fail too early.
      if (
          over_percentage < self._BALANCED_THRESHOLD
          and under_percentage < self._BALANCED_THRESHOLD
      ):
        return ExposureFeedback.BALANCED

    return self._get_directional_feedback()

  def _get_directional_feedback(self) -> ExposureFeedback:
    """Returns OVER or UNDER based on the latest sample."""
    if not self._history:
      return ExposureFeedback.UNDEREXPOSED

    latest = self._history[-1]
    over_percentage = latest.get(ExposureFeedback.OVEREXPOSED.value, 0.0)
    under_percentage = latest.get(ExposureFeedback.UNDEREXPOSED.value, 0.0)
    logging.debug(
        'Exposure: over: %.1f, under: %.1f',
        over_percentage,
        under_percentage,
    )

    if over_percentage > under_percentage:
      return ExposureFeedback.OVEREXPOSED
    return ExposureFeedback.UNDEREXPOSED


class HSVMatchInfoIterator:
  """Iterator for HSV match info from a camera.

  Attributes:
    passport: The passport host to send the HSV analysis request to.
    camera_id: The camera ID to use for the HSV analysis.
    log_path: The log path for debug logs.
    masks: The HSV masks to use for analysis.
    camera_capture_prefix: The prefix to use for the camera capture.
    exposure_times_generator: The generator for exposure times.
    exposure_feedback: The exposure feedback from the last HSV match info.
    exposure_tracker: The exposure stability tracker used to determine when the
      exposure is balanced.

    Yields:
      A tuple of (exposure_time_us, hsv_match_info).
  """

  def __init__(
      self,
      passport: passport_host.PassportHost,
      camera_id: str,
      log_path: str,
      min_exposure: int,
      max_exposure: int,
      masks: dict[str, image.HSVMask],
      camera_capture_prefix: str = '',
      max_iterations: int = 10,
      tolerance: int = 100,
  ):
    self.passport = passport
    self.camera_id = camera_id
    self.log_path = log_path
    self.masks = masks
    self.camera_capture_prefix = camera_capture_prefix

    self.exposure_times_generator = binary_search_exposure(
        min_exposure=min_exposure,
        max_exposure=max_exposure,
        max_iterations=max_iterations,
        tolerance=tolerance,
    )
    self.exposure_tracker = ExposureStabilityTracker()
    self.exposure_feedback = None

  def __iter__(self):
    return self

  def __next__(self):
    """Returns the next exposure time and HSV match info."""
    exposure_time_us = self.exposure_times_generator.send(
        self.exposure_feedback
    )

    hsv_match_info = self._get_hsv_match_info(exposure_time_us)
    self.exposure_tracker.add_sample(hsv_match_info)
    self.exposure_feedback = self.exposure_tracker.get_feedback()
    logging.debug('Exposure feedback: %s', self.exposure_feedback)

    return exposure_time_us, hsv_match_info

  def _get_hsv_match_info(
      self,
      exposure_time_us: int,
  ) -> dict[str, float]:
    """Returns the HSV match info from the HSV analysis."""
    logging.debug(
        'Camera %s Exposure time: %s', self.camera_id, exposure_time_us
    )
    hsv_match_info = self.passport.analyze_hsv(
        self.camera_id,
        self.masks,
        self.log_path,
        f'{self.camera_capture_prefix}{self.camera_id}_{exposure_time_us}'
        if self.camera_capture_prefix
        else '',
        exposure_time_us=exposure_time_us,
    )
    logging.debug('HSV match percentages: %s', hsv_match_info)
    return hsv_match_info


class MatchedColorIterator(HSVMatchInfoIterator):
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
    exposure_tracker: The exposure stability tracker used to determine when the
      exposure is balanced.

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
      camera_capture_prefix: The prefix to use for the camera capture. The
        capture will be saved as
        {log_path}/{timestamp}_{camera_capture_prefix}{camera_id}_{exposure_time_us}.
    """
    super().__init__(
        passport=passport,
        camera_id=camera_id,
        log_path=log_path,
        min_exposure=min_exposure,
        max_exposure=max_exposure,
        masks={**self._HSV_MASKS_PASIT, **_EXPOSURE_FEEDBACK_MASKS},
        camera_capture_prefix=camera_capture_prefix,
    )

  def __next__(self):
    """Returns the next matched color."""
    _, hsv_match_info = super().__next__()
    return self._get_matched_color(hsv_match_info)

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

    match_name = max(
        hsv_match_percentages,
        key=hsv_match_percentages.get,
    )
    if match_name in [e.value for e in ExposureFeedback]:
      return None

    match_percentage = hsv_match_percentages[match_name]
    if match_percentage < self._MATCH_PERCENTAGE_THRESHOLD:
      logging.debug(
          'Did not match any color, max match percentage is %s:%.2f',
          match_name,
          match_percentage,
      )
      return None
    return image.NamedColor[match_name]


def get_camera_exposure(
    camera_id: str,
    passport: passport_host.PassportHost,
    log_path: str,
    min_exposure: int = 0,
    max_exposure: int = 50000,
    camera_capture_prefix: str = 'get_camera_exposure',
) -> int:
  """Determines the optimal exposure for a camera.

  Args:
      camera_id: The camera ID to determine exposure for.
      passport: The passport host to use for analysis.
      log_path: The log path for debug logs.
      min_exposure: The minimum possible exposure value.
      max_exposure: The maximum possible exposure value.
      camera_capture_prefix: The prefix to use for the camera capture.

  Returns:
      int: The optimal exposure value.

  Raises:
      RuntimeError: If optimal exposure cannot be found.
  """
  iterator = HSVMatchInfoIterator(
      passport=passport,
      camera_id=camera_id,
      log_path=log_path,
      min_exposure=min_exposure,
      max_exposure=max_exposure,
      masks=_EXPOSURE_FEEDBACK_MASKS,
      camera_capture_prefix=camera_capture_prefix,
      # since we aren't relying on a color match to help stop the search tweak
      # the tolerance and max iterations to give the stability tracker a better
      # chance to converge.
      max_iterations=15,
      tolerance=10,
  )
  for exposure_time, _ in iterator:
    last_exposure = exposure_time
    if iterator.exposure_feedback == ExposureFeedback.BALANCED:
      return last_exposure

  raise RuntimeError(f'Could not find optimal exposure for camera {camera_id}')
