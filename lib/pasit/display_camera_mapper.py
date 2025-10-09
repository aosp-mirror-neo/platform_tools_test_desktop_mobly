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

"""Helper class for mapping displays to cameras."""

import enum
import logging

from lib.pasit import color_capturer
from lib.pasit import display_painter
from lib.pasit import pasit_display
from lib.pasit.passport import passport_host
from lib.utils import image


class UnexpectedDisplayCountError(Exception):
  """Error when the number of displays detected is unexpected."""


class MapDisplaysToCamerasError(Exception):
  """Error when mapping displays to cameras fails."""


class DisplayPaths(enum.Enum):
  """Enum for the different display paths."""

  DOCK = 'DOCK'
  DOCKLESS = 'DOCKLESS'
  DAISY_CHAIN = 'DAISY_CHAIN'


class DisplayCameraMapper:
  """Helper class for mapping displays to cameras.

  Attributes:
    passport: The passport host to use for the display tools.
    display: The display to use for the display tools.
    painter: The painter to use for the display tools.
    log_path: The log path to use for the display tools.
  """

  DISPLAY_TOPOLOGY_TAGS = [
      'DISPLAY_TOPOLOGY',
      'DISPLAY_TOPOLOGY_WITH_EDID',
  ]

  _COLORS = [
      image.NamedColor.RED,
      image.NamedColor.GREEN,
      image.NamedColor.BLUE,
  ]

  passport: passport_host.PassportHost
  display: pasit_display.PasitDisplay
  painter: display_painter.DisplayPainter
  log_path: str

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

  def map_displays_to_cameras(
      self,
  ) -> dict[pasit_display.PasitDisplay.DisplayId, str]:
    """Maps the displays to cameras.

    This sets up the rgb images on the displays and then tries to match the
    camera captured color to the display color using HSV analysis.  It will try
    multiple exposure times if the camera doesn't match any color.

    Returns:
      A dictionary of display ID to camera ID.

    Raises:
      MapDisplaysToCamerasError: If mapping fails.
    """
    logging.info('Mapping displays to cameras')
    display_id_to_color = self._open_rgb_images_on_displays()
    mapping_result = {}
    unmapped_cameras_to_color = {}

    for camera_id in self.passport.get_cameras():
      display_id, last_color = self._try_match_display_to_camera(
          camera_id, display_id_to_color
      )

      if not display_id:
        logging.warning(
            'Camera %s did not match any display. Skipping.', camera_id
        )
        unmapped_cameras_to_color[camera_id] = last_color
        continue

      if display_id in mapping_result:
        logging.warning(
            'Camera %s matched display %r, but it is already mapped to'
            ' camera id %s',
            camera_id,
            display_id,
            mapping_result[display_id],
        )
        continue

      logging.info(
          'Camera %s matched display %r with color %s',
          camera_id,
          display_id,
          display_id_to_color[display_id].name,
      )
      mapping_result[display_id] = camera_id

    self.painter.clean_color_on_display()

    if len(mapping_result) != len(display_id_to_color):
      error_message = self._create_map_displays_error_message(
          display_id_to_color, mapping_result, unmapped_cameras_to_color
      )
      raise MapDisplaysToCamerasError(error_message)

    logging.debug('Mapping result: %s', mapping_result)
    return mapping_result

  def _create_map_displays_error_message(
      self,
      display_id_to_color: dict[
          pasit_display.PasitDisplay.DisplayId, image.NamedColor
      ],
      mapping_result: dict[pasit_display.PasitDisplay.DisplayId, str],
      unmapped_cameras_to_color: dict[str, image.NamedColor | None],
  ) -> str:
    """Creates an error message for when mapping displays to cameras fails."""
    unmapped_displays = [
        display
        for display in display_id_to_color
        if display not in mapping_result
    ]
    logging.warning('Displays %r did not match any camera.', unmapped_displays)

    unmapped_displays_str = ', '.join(
        [f'"{display!r}"' for display in unmapped_displays]
    )

    unmapped_cameras_str_parts = []
    for camera, color in unmapped_cameras_to_color.items():
      color_name = color.name.title() if color else 'no color'
      unmapped_cameras_str_parts.append(f'{camera} matched {color_name}')
    unmapped_cameras_str = ', '.join(unmapped_cameras_str_parts)

    error_message = f'No camera mapped to display {unmapped_displays_str}'
    if unmapped_cameras_str:
      error_message += f', camera(s) matched no display: {unmapped_cameras_str}'
    return error_message

  def get_display_testing_camera_id(
      self, display_id: pasit_display.PasitDisplay.DisplayId
  ) -> str:
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

  def try_match_color(
      self,
      camera_id: str,
      color: image.NamedColor,
      camera_capture_prefix: str = '',
  ) -> bool:
    """Returns the color captured from the camera.

    Args:
      camera_id: The camera ID to get the color from.
      color: The color to match.
      camera_capture_prefix: The prefix to use for the camera capture.

    Returns:
      True if the color is matched, False otherwise.
    """
    # return the first matched color that is not None, or None if no color is
    # matched.
    last_matched_color = None
    for matched_color in self._get_color_iterator(
        camera_id, camera_capture_prefix
    ):
      if matched_color and matched_color == color:
        return True
      last_matched_color = matched_color
    logging.info(
        'Camera %s did not match color %s. Last matched color: %s',
        camera_id,
        color.name,
        last_matched_color,
    )
    return False

  def _open_rgb_images_on_displays(
      self,
  ) -> dict[pasit_display.PasitDisplay.DisplayId, image.NamedColor]:
    """Opens RGB images on the displays.

    Returns:
      A dictionary of display ID to color.

    Raises:
      UnexpectedDisplayCountError: If there are too many displays detected.
    """
    display_ids = self.display.get_display_ids()
    if len(display_ids) > len(self._COLORS):
      raise UnexpectedDisplayCountError(
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
      display_id_to_color: dict[
          pasit_display.PasitDisplay.DisplayId, image.NamedColor
      ],
  ) -> tuple[
      pasit_display.PasitDisplay.DisplayId | None, image.NamedColor | None
  ]:
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
      A tuple of the display ID that matched the camera and the matched color.
      If mapping fails returns (None, last_matched_color).
    """

    # return the first matched display, or None if no display is matched.
    last_matched_color = None
    for matched_color in self._get_color_iterator(
        camera_id, 'match_display_to_camera'
    ):
      last_matched_color = matched_color
      matched_display_id = self._get_matched_display_id(
          matched_color, display_id_to_color
      )
      if matched_display_id:
        return matched_display_id, matched_color
    return None, last_matched_color

  def _get_color_iterator(
      self,
      camera_id: str,
      camera_capture_prefix: str = '',
  ) -> color_capturer.MatchedColorIterator:
    """Returns an iterator for the color captured from the camera.

    Iterates through the exposure times using binary search, for each exposure
    time, captures an image from the camera, and uses the data from the passport
    HSV analysis to find a matched color. Yields image.NamedColor.
    """
    return color_capturer.MatchedColorIterator(
        self.passport,
        camera_id,
        self.log_path,
        min_exposure=0,
        max_exposure=50000,
        camera_capture_prefix=camera_capture_prefix,
    )

  def _get_matched_display_id(
      self,
      matched_color: image.NamedColor | None,
      display_id_to_color: dict[
          pasit_display.PasitDisplay.DisplayId, image.NamedColor
      ],
  ) -> pasit_display.PasitDisplay.DisplayId | None:
    """Returns the display ID that matches the color captured from the camera.

    Args:
      matched_color: The color captured from the camera.
      display_id_to_color: A dictionary of display ID to the color that is
        displayed on the display.

    Returns:
      The display ID that matches the color captured from the camera, or None if
      no display matches the color.
    """
    if matched_color is None:
      return None

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
