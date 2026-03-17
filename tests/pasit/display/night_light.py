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

from lib.pasit import color_capturer
from lib.pasit import peripheral_connector
from lib.utils import functools
from lib.utils import image
from mobly import asserts
from mobly import test_runner
from pasit.display import display_base_test

_NIGHT_LIGHT_TEMP_WARM = 2597
_NIGHT_LIGHT_TEMP_COOL = 4000


@functools.generate_tests
class NightLightTest(display_base_test.DisplayBaseTest):
  """Verifies color temperature shift on internal and external screens."""

  def teardown_test(self):
    """Handle the teardown for the test."""
    super().teardown_test()  # pylint: disable=attribute-error
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
    external_ids = self.helper.get_external_display_ids(external_display_count)
    all_displays = [internal_id] + external_ids
    exposure_map = {}

    for display_id in all_displays:
      # Muted Blue provides a reliable margin for intensity based assertion.
      logging.info('Showing Muted Blue on display %s.', display_id)
      self.painter.show_color_on_display(
          image.NamedColor.MUTED_BLUE.value, display_id
      )
      logging.debug(
          'Calculating fixed exposure for camera %s on display %s.',
          display_map[display_id],
          display_id,
      )
      exposure_map[display_id] = color_capturer.get_camera_exposure(
          camera_id=display_map[display_id],
          passport=self.passport_host,
          log_path=self.current_test_info.output_path,
      )
    self.capture_screenshots('after_muted_blue_on_display')

    warmth_scores = {d: {} for d in all_displays}

    logging.info('Disabling Night Light for baseline capture.')
    self.display.set_night_light_enabled(False)

    self._get_all_display_warmth_scores(
        all_displays, display_map, 'baseline_off', warmth_scores, exposure_map
    )

    logging.info('Enabling Night Light.')
    self.display.set_night_light_enabled(True)

    logging.info('Triggering Night Light change: %dK', _NIGHT_LIGHT_TEMP_WARM)
    self.display.set_night_light_temperature(_NIGHT_LIGHT_TEMP_WARM)
    asserts.assert_equal(
        _NIGHT_LIGHT_TEMP_WARM, self.display.get_night_light_temperature()
    )
    self._get_all_display_warmth_scores(
        all_displays,
        display_map,
        _NIGHT_LIGHT_TEMP_WARM,
        warmth_scores,
        exposure_map,
    )

    logging.info('Triggering Night Light change: %dK', _NIGHT_LIGHT_TEMP_COOL)
    self.display.set_night_light_temperature(_NIGHT_LIGHT_TEMP_COOL)
    asserts.assert_equal(
        _NIGHT_LIGHT_TEMP_COOL, self.display.get_night_light_temperature()
    )
    self._get_all_display_warmth_scores(
        all_displays,
        display_map,
        _NIGHT_LIGHT_TEMP_COOL,
        warmth_scores,
        exposure_map,
    )

    for display_id in all_displays:
      baseline_score = warmth_scores[display_id]['baseline_off']
      warm_setting_score = warmth_scores[display_id][_NIGHT_LIGHT_TEMP_WARM]
      cool_setting_score = warmth_scores[display_id][_NIGHT_LIGHT_TEMP_COOL]

      logging.info(
          'Display %s | Nightlight off: %.2f | Nightlight Cool: %.2f |'
          ' Nightlight Warm: %.2f',
          display_id,
          baseline_score,
          cool_setting_score,
          warm_setting_score,
      )
      # TODO: b/491020824 - Night light intensity fails to update
      # visually despite successful assertion
      #   asserts.assert_greater(
      #       warm_setting_score,
      #       cool_setting_score,
      #       f'Display {display_id}: Night light validation failed. '
      #       f'Expected warm setting score to be higher than '
      #       f'cool setting score.'
      #     )

      asserts.assert_greater(
          cool_setting_score,
          baseline_score,
          f'Display {display_id}: Night light validation failed. '
          'Expected cool setting score to be higher than baseline score.',
      )

  def _get_all_display_warmth_scores(
      self,
      display_ids: list[str],
      display_map: dict[str, str],
      temp_label: int | str,
      warmth_dict: dict[str, dict[str | int, float]],
      exposure_map: dict[str, int],
  ) -> None:
    """Helper to capture warmth scores for all displays at a specific state."""
    for display_id in display_ids:
      warmth_dict[display_id][temp_label] = self._get_warmth_score(
          display_id, display_map, str(temp_label), exposure_map[display_id]
      )

  def _get_warmth_score(
      self,
      display_id: str,
      display_map: dict[str, str],
      label: str,
      captured_exposure: int,
  ) -> float:
    camera_id = display_map[display_id]
    return self.passport_host.get_warmth_score(
        camera_id=camera_id,
        log_dir=self.current_test_info.output_path,
        image_name_suffix=f'nightlight_{display_id}_{label}',
        exposure_time_us=captured_exposure,
    )


if __name__ == '__main__':
  test_runner.main()
