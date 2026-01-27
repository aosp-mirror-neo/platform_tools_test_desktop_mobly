# Copyright 2026 Google LLC
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

"""Test night light mode with single/dual display configuration with dock/dockless paths."""

import logging

from lib.pasit import peripheral_connector
from lib.utils import functools
from lib.utils import image
from mobly import asserts
from mobly import test_runner
from pasit.display import display_base_test


@functools.generate_tests
class NightLightTest(display_base_test.DisplayBaseTest):
  """Verifies color temperature shift on internal and external screens."""

  def teardown_test(self):
    """Handle the teardown for the test."""
    super().teardown_test()
    self.display.set_night_light_enabled(False)

  @functools.with_variants(
      one_display_dock=(1, peripheral_connector.ConnectionType.DOCK),
      one_display_dockless=(1, peripheral_connector.ConnectionType.DOCKLESS),
      two_displays_dock=(2, peripheral_connector.ConnectionType.DOCK),
      two_displays_daisy_chain=(
          2,
          peripheral_connector.ConnectionType.DAISY_CHAIN,
      ),
  )
  def test_night_light_with(
      self,
      external_display_count: int,
      connection_type: peripheral_connector.ConnectionType,
  ) -> None:
    """Verifies the Night Light color temperature shift on multiple displays.

    Args:
      external_display_count: Number of external monitors to plug in.
      connection_type: The physical connection method.
    """
    internal_id = self.helper.get_internal_display_id()
    self.plug_in_external_displays(external_display_count, connection_type)
    self.verify_display_count(external_display_count + 1, 'after plug-in')

    display_map = self.map_displays_to_cameras_with_retries()
    external_ids = self.helper.get_external_display_ids(
        internal_id, external_display_count
    )
    all_displays = [internal_id] + external_ids

    for display_id in all_displays:
      # Muted Blue provides a reliable margin for intensity based assertion.
      logging.info('Showing Muted Blue on display %s.', display_id)
      self.painter.show_color_on_display(
          image.NamedColor.MUTED_BLUE.value, display_id
      )
    self.capture_screenshots('after_muted_blue_on_display')

    logging.info('Disabling Night Light for baseline capture.')
    self.display.set_night_light_enabled(False)
    asserts.assert_false(
        self.display.get_night_light_enabled(), 'Night Light should be OFF'
    )

    baseline_warmth = {
        d: self._get_warmth_score(d, display_map, 'baseline_off')
        for d in all_displays
    }

    logging.info('Enabling Night Light.')
    self.display.set_night_light_enabled(True)
    asserts.assert_true(
        self.display.get_night_light_enabled(), 'Night Light should be ON'
    )

    for display_id in all_displays:
      self.display.set_night_light_temperature(0)
      asserts.assert_equal(
          0,
          self.display.get_night_light_temperature(),
          'Night light temperature is not set correctly.',
      )
      warmth_0 = self._get_warmth_score(display_id, display_map, 'temp_0')

      self.display.set_night_light_temperature(100)
      asserts.assert_equal(
          100,
          self.display.get_night_light_temperature(),
          'Night light temperature is not set correctly.',
      )
      warmth_100 = self._get_warmth_score(display_id, display_map, 'temp_100')

      logging.info(
          'Display %s | Baseline: %d | Temp 0: %d | Temp 100: %d',
          display_id,
          baseline_warmth[display_id],
          warmth_0,
          warmth_100,
      )

      asserts.assert_greater(
          warmth_100,
          warmth_0,
          f'Display {display_id}: Temp 100 should be warmer than Temp 0.',
      )

      asserts.assert_greater(
          warmth_100,
          baseline_warmth[display_id],
          f'Display {display_id}: Temp 100 should be warmer than Baseline.',
      )

  def _get_warmth_score(
      self, display_id: str, display_map: dict[str, str], label: str
  ) -> int:
    """Helper to capture raw RGB average and calculate hot-cold score.

    Args:
      display_id: The ID of the display to capture.
      display_map: A dictionary mapping display IDs to camera IDs.
      label: A label to use in the saved image filename.

    Returns:
      An integer representing the warmth score (higher values indicate warmer
      colors).
    """
    camera_id = display_map[display_id]

    avg_rgb_color = self.passport_host.get_average_pixel(
        camera_id=camera_id,
        log_dir=self.current_test_info.output_path,
        image_name_suffix=f'nightlight_{display_id}_{label}',
    )

    return image.get_color_hot_cold(avg_rgb_color)


if __name__ == '__main__':
  test_runner.main()
