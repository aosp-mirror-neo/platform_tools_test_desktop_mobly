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

"""Helper class for display testing tools for PASIT tests."""

import logging
from typing import Optional

from lib.pasit import display_painter
from lib.pasit import pasit_display
from lib.pasit.passport import passport_host
from lib.utils import image
from lib.utils import retry
from mobly import signals


class DisplayHelper:
  """Helper class for display testing tools for PASIT tests.

  Attributes:
    passport: The passport host to use for the display tools.
    display: The display to use for the display tools.
    painter: The painter to use for the display tools.
    log_path: The log path to use for the display tools.
    camera_exposure_time_us: The camera exposure time in microseconds to use for
      the display tools.
  """

  # HSV masks for PASIT displays. +/-30 degrees from the expected color gives
  # reasonable results, with the exception of green which has more on the plus
  # end to make it pass on sample set of images in passport unit tests.
  _HSV_MASKS_PASIT = {
      image.NamedColor.RED.name: image.HSVMask(
          image.HSV(h=330, s=0.5, v=0.55),
          image.HSV(h=30, s=1.0, v=1.0),
      ),
      image.NamedColor.GREEN.name: image.HSVMask(
          image.HSV(h=90, s=0.5, v=0.55),
          image.HSV(h=165, s=1.0, v=1.0),
      ),
      image.NamedColor.BLUE.name: image.HSVMask(
          image.HSV(h=210, s=0.5, v=0.55),
          image.HSV(h=270, s=1.0, v=1.0),
      ),
      image.NamedColor.BLACK.name: image.HSVMask(
          image.HSV(h=0, s=0, v=0),
          image.HSV(h=360, s=1.0, v=0.5),
      ),
  }

  # The minimum percentage of pixels that must match for a color to be
  # considered a match, we set this to a low value because glare on the display
  # can cause a lot of pixels to be washed out and close to white rather than
  # the expected color.
  _MATCH_PERCENTAGE_THRESHOLD = 40.0

  _COLORS = [
      image.NamedColor.RED,
      image.NamedColor.GREEN,
      image.NamedColor.BLUE,
  ]

  passport: passport_host.PassportHost
  display: pasit_display.PasitDisplay
  painter: display_painter.DisplayPainter
  log_path: str

  camera_exposure_time_us: int = 0

  def __init__(
      self,
      passport: passport_host.PassportHost,
      display: pasit_display.PasitDisplay,
      painter: display_painter.DisplayPainter,
      log_path: str,
  ):
    """Initializes the display tools.

    Args:
      passport: The passport host to use for the display tools.
      display: The display to use for the display tools.
      painter: The painter to use for the display tools.
      log_path: The log path to use for the display tools.
    """
    self.passport = passport
    self.display = display
    self.painter = painter
    self.log_path = log_path

  def get_internal_display_id(self) -> str:
    """Returns the internal display ID.

    This function assumes that there is only one display plugged in.

    Raises:
      signals.TestError: If the DUT has more than one display plugged in.
    """
    display_ids = self.display.get_display_ids()
    if len(display_ids) > 1:
      raise signals.TestError(
          'This method should be called when there is only one display'
          ' plugged in.'
      )
    logging.debug('Internal display id: %s', display_ids[0])
    return display_ids[0]

  def get_external_display_id(self, internal_display_id: str) -> str:
    """Returns the external display ID.

    This function assumes that there is only one external display plugged in.

    Raises:
      signals.TestError: If the DUT does not have exactly one external display.
    """
    display_ids = self.display.get_display_ids()
    if len(display_ids) != 2:
      raise signals.TestError(
          'This method should be called when there is exactly one external'
          ' display plugged in.'
      )
    external_display_ids = [
        display_id
        for display_id in display_ids
        if display_id != internal_display_id
    ]
    if len(external_display_ids) != 1:
      raise signals.TestError(
          'Unexpected number of external displays found'
          f' {len(external_display_ids)}.'
      )
    logging.debug('External display id: %s', external_display_ids[0])
    return external_display_ids[0]

  def map_displays_to_cameras(self) -> dict[str, str]:
    """Maps the camera to the display.

    This sets up the rgb images on the displays and then tries to match the
    camera color to the display color using HSV analysis.  It will try multiple
    exposure times if the camera doesn't match any color.

    Returns:
      A dictionary of display ID to camera ID.
    Raises:
      signals.TestError: If not all displays have a camera detected.
    """
    logging.info('Mapping displays to cameras')
    display_id_to_color = self._open_rgb_images_on_displays()

    # Try different exposure times to see if we can get a good match.
    # testing shows that lower exposure times are more reliable and less
    # affected by glare and overexposure, so start with those and then try 0
    # which is auto exposure as a last resort.
    exposure_times_to_try = [3000, 6000, 12000, 0]
    exposure_times_generator = (
        exposure_time for exposure_time in exposure_times_to_try
    )
    mapping_result = retry.retry(
        lambda: self._check_hsv_matches_displays(
            display_id_to_color, next(exposure_times_generator)
        ),
        max_tries=len(exposure_times_to_try),
        exceptions=(signals.TestError,),
    )
    self.painter.clean_color_on_display()
    logging.debug('Mapping result: %s', mapping_result)
    return mapping_result

  def _get_matched_color(
      self,
      hsv_match_percentages: dict[str, float],
  ) -> Optional[image.NamedColor]:
    """Verifies that the display captured the expected color."""
    # handle the case where are hsv percentage values are 0 since protobuf
    # optimizes out the 0 values we end up with an empty dict.
    if not hsv_match_percentages:
      logging.debug('HSV match percentages are empty')
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
    match_color = image.NamedColor[match_color]
    return match_color

  def get_display_testing_camera_id(self, display_id: str) -> str:
    """Returns an ID for the camera that is pointed at the given display.

    Perform the mapping of displays to cameras. Any color displayed before
    calling this function will be overwritten.

    Args:
      display_id: The display ID to get the camera ID for.

    Raises:
      ValueError: If the display ID is not valid.

    Returns:
      The camera ID for the given display ID.
    """
    display_id_to_camera_id = self.map_displays_to_cameras()
    if display_id not in display_id_to_camera_id:
      raise ValueError(f'Display ID {display_id} is not valid.')
    return display_id_to_camera_id[display_id]

  def capture_color(
      self,
      camera_id: str,
      camera_capture_prefix: str = '',
  ) -> Optional[image.NamedColor]:
    """Returns the color captured from the camera.

    Args:
      camera_id: The camera ID to get the color from.
      camera_capture_prefix: The prefix to use for the camera capture.

    Returns:
      The color from the camera, or None if no color is matched.
    """
    hsv_match_percentages = self.passport.analyze_hsv(
        camera_id,
        self._HSV_MASKS_PASIT,
        self.log_path,
        camera_capture_prefix,
        self.camera_exposure_time_us,
    )
    logging.debug('Verifying HSV match percentages: %s', hsv_match_percentages)
    return self._get_matched_color(hsv_match_percentages)

  def _open_rgb_images_on_displays(self) -> dict[str, image.Color]:
    """Opens RGB images on the displays.

    Returns:
      A dictionary of display ID to color.

    Raises:
      signals.TestError: If there are too many displays detected.
    """
    display_ids = self.display.get_display_ids()
    if len(display_ids) > len(self._COLORS):
      raise signals.TestError(
          'Too many displays detected. Expected at most'
          f' {len(self._COLORS)} displays, but got {len(display_ids)}.'
      )

    display_id_to_color = dict(
        zip(display_ids, [color.value for color in self._COLORS])
    )
    for display_id, color in display_id_to_color.items():
      self.painter.show_color_on_display(color, display_id)
    return display_id_to_color

  def _check_hsv_matches_displays(
      self, display_id_to_color: dict[str, image.Color], exposure_time_us: int
  ) -> dict[str, str]:
    """Does the matching part of _map_displays_to_cameras.

    This does the actual matching of cameras to displays using HSV analysis,
    first captures an image from each camera with the specified exposure time,
    then analyzes the data from the passport HSV analysis to see there is a
    color match.

    Args:
      display_id_to_color: A dictionary of display ID to color.
      exposure_time_us: The exposure time in microseconds to use for the camera.

    Returns:
      A dictionary of display ID to camera ID.
    Raises:
      signals.TestError: If not all displays have a camera detected.
    """
    logging.debug(
        'Trying to map displays to cameras with exposure time %d us',
        exposure_time_us,
    )
    hsv_match_percentages = {
        camera_id: self.passport.analyze_hsv(
            camera_id,
            self._HSV_MASKS_PASIT,
            self.log_path,
            f'camera_capture_{camera_id}_{exposure_time_us}',
            exposure_time_us=exposure_time_us,
        )
        for camera_id in self.passport.get_cameras()
    }
    logging.debug('HSV match percentages: %s', hsv_match_percentages)

    display_id_to_camera_id = dict()
    for camera_id, hsv_match_percentages in hsv_match_percentages.items():
      matched_color = self._get_matched_color(hsv_match_percentages)
      if matched_color is None:
        # Camera didn't match any color or is not properly aligned so skip it
        # since we associated it with any display.
        continue
      matched_display_id = None
      for display_id, color in display_id_to_color.items():
        if color == matched_color.value:
          matched_display_id = display_id
          break
      if matched_display_id is None:
        logging.info(
            f'Camera {camera_id} matched color {matched_color} but no display'
            ' matched it.'
        )
        continue
      logging.info(
          'Camera %s matched color %s  on display %s with %.1f%% of pixels'
          ' matching',
          camera_id,
          matched_color.name,
          matched_display_id,
          hsv_match_percentages[matched_color.name],
      )
      # store the association between the matched display id and the camera id
      display_id_to_camera_id[matched_display_id] = camera_id
    logging.debug('Display id to camera id: %s', display_id_to_camera_id)
    if len(display_id_to_camera_id) != len(display_id_to_color):
      raise signals.TestError(
          'Not all displays have a camera associated with them. '
          'Check that cameras are aligned and displays are functioning.'
          f'Expected {len(display_id_to_color)} displays, but got'
          f' {len(display_id_to_camera_id)}.'
      )
    # if we get a match, store the exposure time to use for future
    # verification steps and image captures.
    self.camera_exposure_time_us = exposure_time_us
    return display_id_to_camera_id
