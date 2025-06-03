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

"""Base test for PASIT display tests."""

import logging

from lib.pasit import pasit_display
from lib.pasit import pasit_test
from mobly import asserts
from mobly import records
from mobly import signals
from utils import image
from utils import retry


class DisplayBaseTest(pasit_test.PasitTestClass):
  """Base test for PASIT display tests."""

  _COLORS = [
      image.NamedColor.RED,
      image.NamedColor.GREEN,
      image.NamedColor.BLUE,
  ]

  _COLOR_EUCLIDEAN_DISTANCE_THRESHOLD = 150

  display: pasit_display.PasitDisplay
  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_MONITOR

  def setup_class(self):
    """Handle the setup for the test.

    Create PasitDisplay for the interacting with displays.
    """
    super().setup_class()
    self.display = self.create(pasit_display)

  def on_fail(self, record: records.TestResultRecord) -> None:
    """Called on test failure."""
    self._capture_display_images('on_fail')
    super().on_fail(record)

  def _plug_in_external_display(self):
    """Emulate external display plug in using passport."""
    logging.info('Plugging in external display')
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_MONITOR)

  def _unplug_external_display(self):
    """Emulate external display unplug using passport."""
    logging.info('Unplugging external display')
    self.passport_host.deactivate_device_by_type(self.DEVICE_TYPE_MONITOR)

  def _verify_display_count(self, expected_count: int, event_to_log: str):
    """Verifies that the display count is equal to the expected count."""
    asserts.assert_equal(
        retry.retry(
            self.display.get_display_count,
            until=lambda count: count == expected_count,
            max_tries=10,
            delay_seconds=2,
        ),
        expected_count,
        f'Display count is not {expected_count} {event_to_log}.',
    )

  def _capture_display_images(self, image_prefix: str):
    """Captures an image from each PASIT camera to the log directory.

    TODO: this doesn't do any association between the image and the display,
    that will be done in future improvements.

    Args:
      image_prefix: The prefix of the image name to use for the image.
    """
    cameras = self.passport_host.get_cameras()
    for camera in cameras:
      logging.debug(
          'Capturing display image for %s camera %s to directory %s',
          image_prefix,
          camera,
          self.current_test_info.output_path,
      )
      self.passport_host.capture_image(
          camera,
          self.current_test_info.output_path,
          f'{image_prefix}_camera{camera}',
      )

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
      self.dut.show_color_on_display(color, display_id)
    return display_id_to_color

  def _map_displays_to_cameras(self) -> dict[str, str]:
    """Maps the camera to the display.

    Returns:
      A dictionary of display ID to camera ID.

    Raises:
      signals.TestError: If not all displays have a camera detected.
    """
    logging.info('Mapping displays to cameras')
    display_id_to_color = self._open_rgb_images_on_displays()
    self.dut.get_screenshots(self.log_path, 'map_displays_to_cameras')

    avg_pixels = {
        camera_id: self.passport_host.get_average_pixel(
            camera_id, self.log_path, f'map_displays_to_cameras{camera_id}'
        )
        for camera_id in self.passport_host.get_cameras()
    }
    logging.debug('Average pixels: %s', avg_pixels)
    self.dut.clean_color_on_display()

    display_id_to_camera_id = dict()
    for camera_id, avg_pixel in avg_pixels.items():
      # for the camera id and its average pixel color captured, calculate the
      # color diff with each display color
      display_id_and_color_diffs = [
          (display_id, image.color_diff(avg_pixel, display_color))
          for display_id, display_color in display_id_to_color.items()
      ]
      # find the display id with the minimum color diff
      min_color_diff_pair = min(
          display_id_and_color_diffs,
          key=lambda display_id_and_color_diff: display_id_and_color_diff[1],
      )
      matched_display_id = min_color_diff_pair[0]
      logging.info(
          'Camera %s captured a color %s that is %.2f from the color %s shown'
          ' on the display %s',
          camera_id,
          str(avg_pixel),
          min_color_diff_pair[1],
          display_id_to_color[matched_display_id],
          matched_display_id,
      )
      # store the association between the matched display id and the camera id
      display_id_to_camera_id[matched_display_id] = camera_id
    logging.debug('Display id to camera id: %s', display_id_to_camera_id)
    if len(display_id_to_camera_id) != len(display_id_to_color):
      raise signals.TestError(
          'Not all displays have a camera associated with them. Expected'
          f' {len(display_id_to_color)} displays, but got'
          f' {len(display_id_to_camera_id)}.'
      )
    return display_id_to_camera_id

  def _verify_captured_color(
      self,
      camera_id: str,
      expected_color: image.Color,
      camera_capture_name: str,
      failure_message: str,
  ):
    """Verifies that the camera captured the expected color.

    Fails the test if the verification fails.

    Args:
      camera_id: The camera ID to use for the verification.
      expected_color: The expected color to verify.
      camera_capture_name: Prefix for the image name to use for the capture.
      failure_message: The message to use for the assertion if the verification
        fails.
    """
    average_pixel = self.passport_host.get_average_pixel(
        camera_id,
        self.log_path,
        f'{camera_capture_name}_from_camera{camera_id}',
    )
    color_diff = image.color_diff(average_pixel, expected_color)
    logging.info(
        'Camera %s captured a color %s that is %.2f from the color %s shown on'
        ' the display',
        camera_id,
        str(average_pixel),
        color_diff,
        expected_color,
    )
    asserts.assert_less_equal(
        color_diff, self._COLOR_EUCLIDEAN_DISTANCE_THRESHOLD, failure_message
    )

  def _get_internal_display_id(self) -> str:
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
    return display_ids[0]

  def _get_external_display_id(self, internal_display_id: str) -> str:
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

    return external_display_ids[0]
