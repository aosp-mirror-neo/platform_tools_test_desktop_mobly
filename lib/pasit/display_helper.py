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

import enum
import logging

from lib.pasit import display_painter
from lib.pasit import pasit_display
from lib.pasit.passport import passport_host
from lib.utils import image
from mobly import signals


class DisplayPaths(enum.Enum):
  """Enum for the different display paths."""

  DOCK = 'DOCK'
  DOCKLESS = 'DOCKLESS'
  DAISY_CHAIN = 'DAISY_CHAIN'


class DisplayHelper:
  """Helper class for display testing tools for PASIT tests.

  Attributes:
    passport: The passport host to use for the display tools.
    display: The display to use for the display tools.
    painter: The painter to use for the display tools.
    log_path: The log path to use for the display tools.
    camera_exposure_time_us: Exposure times to use for each camera. This is used
      to capture images from the cameras and verify the colors on the displays.
  """

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
          image.HSV(h=360, s=0.4, v=0.6),
      ),
      image.UNDEREXPOSED: image.HSVMask(
          image.HSV(h=0, s=0, v=0),
          image.HSV(h=360, s=1.0, v=0.5),
      ),
      image.OVEREXPOSED: image.HSVMask(
          image.HSV(h=0, s=0, v=0.85),
          image.HSV(h=360, s=1.0, v=1.0),
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

  DISPLAY_TOPOLOGY_TAGS = [
      'DISPLAY_TOPOLOGY',
      'DISPLAY_TOPOLOGY_WITH_EDID',
  ]

  passport: passport_host.PassportHost
  display: pasit_display.PasitDisplay
  painter: display_painter.DisplayPainter
  log_path: str

  camera_exposure_time_us: dict[str, int] = {}

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
    """Maps the displays to cameras.

    This sets up the rgb images on the displays and then tries to match the
    camera captured color to the display color using HSV analysis.  It will try
    multiple exposure times if the camera doesn't match any color.

    Returns:
      A dictionary of display ID to camera ID.

    Raises:
      signals.TestError: If mapping fails.
    """
    logging.info('Mapping displays to cameras')
    display_id_to_color = self._open_rgb_images_on_displays()
    mapping_result = {}

    for camera_id in self.passport.get_cameras():
      display_id = self._try_match_display_to_camera(
          camera_id, display_id_to_color
      )

      if not display_id:
        logging.warning(
            'Camera %s did not match any display. Skipping.', camera_id
        )
        continue

      if display_id in mapping_result:
        logging.warning(
            'Camera %s matched display id %s, but it is already mapped to'
            ' camera id %s',
            camera_id,
            display_id,
            mapping_result[display_id],
        )
        continue

      logging.info(
          'Camera %s matched display id %s',
          camera_id,
          display_id,
      )
      mapping_result[display_id] = camera_id

    self.painter.clean_color_on_display()

    if len(mapping_result) != len(display_id_to_color):
      logging.warning(
          'Displays %s did not match any camera.',
          [
              display_id
              for display_id in display_id_to_color
              if display_id not in mapping_result
          ],
      )
      raise signals.TestError(
          'Failed to map displays to cameras. Check that cameras are aligned'
          ' and displays are functioning.'
      )

    logging.debug('Mapping result: %s', mapping_result)
    return mapping_result

  def _get_matched_color(
      self,
      hsv_match_percentages: dict[str, float],
  ) -> image.NamedColor | None:
    """Returns the matched color from the HSV match percentages."""
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
  ) -> str | None:
    """Returns the exposure feedback from the HSV match info."""
    overexposed_percent = hsv_match_info.get(image.OVEREXPOSED, 0)
    underexposed_percent = hsv_match_info.get(image.UNDEREXPOSED, 0)
    if overexposed_percent > underexposed_percent:
      return image.OVEREXPOSED
    if underexposed_percent > overexposed_percent:
      return image.UNDEREXPOSED
    return None

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
  ) -> image.NamedColor | None:
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
        self.camera_exposure_time_us.get(camera_id, 0),
    )
    logging.debug(
        'HSV match percentages for camera %s: %s',
        camera_id,
        hsv_match_percentages,
    )
    return self._get_matched_color(hsv_match_percentages)

  def _open_rgb_images_on_displays(self) -> dict[str, image.NamedColor]:
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

    display_id_to_color = dict(zip(display_ids, self._COLORS))
    for display_id, color in display_id_to_color.items():
      self.painter.show_color_on_display(color.value, display_id)
    return display_id_to_color

  def _try_match_display_to_camera(
      self,
      camera_id: str,
      display_id_to_color: dict[str, image.NamedColor],
  ) -> str | None:
    """Tries to map a display to a camera.

    Matches the color displayed on the display to the color captured from the
    camera using HSV analysis:
    - iterates through the exposure times using binary search,
    - for each exposure time, captures an image from the camera,
    - and uses the data from the passport HSV analysis to find a matched color,
    - then finds a display that rendered the matched color.

    Args:
      camera_id: The camera ID to use for the mapping.
      display_id_to_color: A dictionary of display ID to color rendered on this
        display.

    Returns:
      A display ID that matched the camera. If mapping fails returns None.
    """
    exposure_times_generator = image.binary_search_exposure(
        min_exposure=0, max_exposure=50000
    )
    exposure_feedback = None
    # TODO: b/435720733 - clean up loop logic
    while True:
      try:
        exposure_time_us = exposure_times_generator.send(exposure_feedback)
      except StopIteration:
        logging.debug('No more exposure times to try.')
        break

      hsv_match_info = self._get_hsv_match_info(
          camera_id,
          f'hsv_match_camera',
          exposure_time_us,
      )

      exposure_feedback = self._get_exposure_feedback(hsv_match_info)
      logging.debug(f'Exposure feedback: {exposure_feedback}')
      matched_color = self._get_matched_color(hsv_match_info)
      if matched_color is None:
        continue

      display_id = self._get_matched_display_id(
          matched_color, display_id_to_color
      )
      if display_id is None:
        continue

      # If we get a match, store the exposure time to use for future
      # verification steps and image captures.
      self.camera_exposure_time_us[camera_id] = exposure_time_us
      return display_id

    return None

  def _get_hsv_match_info(
      self,
      camera_id: str,
      camera_capture_prefix: str,
      exposure_time_us: int,
  ) -> dict[str, float]:
    logging.debug(f'Camera {camera_id} Exposure time: {exposure_time_us}')
    hsv_match_info = self.passport.analyze_hsv(
        camera_id,
        self._HSV_MASKS_PASIT,
        self.log_path,
        f'{camera_capture_prefix}{camera_id}_{exposure_time_us}',
        exposure_time_us,
    )
    logging.debug('HSV match percentages: %s', hsv_match_info)
    return hsv_match_info

  def _get_matched_display_id(
      self,
      matched_color: image.NamedColor,
      display_id_to_color: dict[str, image.NamedColor],
  ) -> str | None:
    """Returns the display ID that matches the color captured from the camera.

    Args:
      matched_color: The color captured from the camera.
      display_id_to_color: A dictionary of display ID to the color that is
        displayed on the display.

    Returns:
      The display ID that matches the color captured from the camera, or None if
      no display matches the color.
    """
    matched_display_ids = [
        display_id
        for display_id, color in display_id_to_color.items()
        if color == matched_color
    ]

    if len(matched_display_ids) > 1:
      logging.debug(
          'Camera matched color %s but multiple displays matched it: %s.',
          matched_color.name,
          matched_display_ids,
      )
      return None

    if not matched_display_ids:
      logging.debug(
          'Camera matched color %s but no display matched it.',
          matched_color.name,
      )
      return None

    matched_display_id = matched_display_ids[0]
    logging.debug(
        'Camera captured color %s that matched display %s.',
        matched_color.name,
        matched_display_id,
    )
    return matched_display_id
