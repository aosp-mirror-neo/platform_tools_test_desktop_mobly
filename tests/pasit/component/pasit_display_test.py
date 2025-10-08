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

"""A test that exercises PASIT Display component tests."""

import enum
import logging
from lib.pasit import display_helper
from lib.pasit import display_painter
from lib.pasit import pasit_display
from lib.pasit import pasit_test
from lib.pasit import test_policy
from lib.utils import functools
from lib.utils import retry
from mobly import asserts
from mobly import test_runner


class DisplayIdType(enum.StrEnum):
  NONE = 'no_display_id'
  INTERNAL = 'internal_display'
  EXTERNAL = 'external_display'


@functools.generate_tests
class PasitDisplayTest(pasit_test.PasitTestClass):

  display: pasit_display.PasitDisplay
  painter: display_painter.DisplayPainter
  helper: display_helper.DisplayHelper
  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_MONITOR

  def setup_class(self):
    super().setup_class()
    self.display = self.create(pasit_display)
    self.painter = self.create(display_painter)

  def setup_test(self):
    """Handle the setup for the test."""
    super().setup_test()
    self.helper = display_helper.DisplayHelper(
        self.passport_host,
        self.display,
        self.painter,
        self.current_test_info.output_path,
    )

  def teardown_test(self):
    """Handle the teardown for the test."""
    self.display.save_debug_info(self.current_test_info.output_path)
    super().teardown_test()

  def test_get_display_ids(self):
    display_ids = self.display.get_display_ids()
    logging.info('Display IDs before external display plug in: %s', display_ids)
    asserts.assert_equal(len(display_ids), 1, 'Display IDs count is not 1.')
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_MONITOR)
    EXPECTED_DISPLAY_COUNT = 2
    display_ids = retry.retry(
        self.display.get_display_ids,
        until=lambda display_ids: len(display_ids) == EXPECTED_DISPLAY_COUNT,
        policy=test_policy.DisplayTestPolicy.EXPECTED_DISPLAY_COUNT_RETRY_POLICY,
    )
    logging.info('Display IDs after external display plug in: %s', display_ids)
    asserts.assert_equal(
        len(display_ids),
        EXPECTED_DISPLAY_COUNT,
        f'Display IDs count is not {EXPECTED_DISPLAY_COUNT}.',
    )

  @functools.with_variants(
      internal=(DisplayIdType.INTERNAL,),
      external=(DisplayIdType.EXTERNAL,),
      none=(DisplayIdType.NONE,),
  )
  def test_get_set_supported_display_resolutions(
      self, display_id_type: DisplayIdType
  ):
    match display_id_type:
      case DisplayIdType.INTERNAL:
        display_id = self.helper.get_internal_display_id()
      case DisplayIdType.EXTERNAL:
        display_id = self._plug_in_external_display()
      case DisplayIdType.NONE:
        display_id = None
      case _:
        raise ValueError(f'Unsupported display ID type: {display_id_type}')

    initial_display_resolution = self.display.get_display_resolution(display_id)
    logging.info(
        'Initial display resolution for display id %s: %s',
        display_id,
        initial_display_resolution,
    )

    supported_resolutions = self.display.get_supported_display_resolutions(
        display_id
    )
    logging.info(
        'Supported resolutions for display id %s: %s',
        display_id,
        supported_resolutions,
    )

    for display_mode_id, display_resolution in supported_resolutions.items():
      logging.info(
          'Setting display resolution for display id %s to %s, %s',
          display_id,
          display_mode_id,
          display_resolution,
      )
      self.display.set_display_resolution(display_mode_id, display_id)
      asserts.assert_equal(
          retry.retry(
              lambda: self.display.get_display_resolution(display_id),
              until=lambda resolution: resolution[0] == display_mode_id,
              policy=test_policy.DisplayTestPolicy.DISPLAY_RESOLUTION_CHANGED_RETRY_POLICY,
          ),
          (display_mode_id, display_resolution),
          'Display resolution is not set correctly.',
      )
    self.display.set_display_resolution(
        initial_display_resolution[0], display_id
    )

  def test_get_set_night_light(self):
    night_light_enabled = self.display.get_night_light_enabled()
    logging.info('Night light is enabled: %s', night_light_enabled)

    logging.info('Setting night light to %s', not night_light_enabled)
    self.display.set_night_light_enabled(not night_light_enabled)
    asserts.assert_equal(
        self.display.get_night_light_enabled(),
        not night_light_enabled,
        'Night light is not set correctly.',
    )

    logging.info('Setting night light to %s', night_light_enabled)
    self.display.set_night_light_enabled(night_light_enabled)
    asserts.assert_equal(
        self.display.get_night_light_enabled(),
        night_light_enabled,
        'Night light is not set correctly.',
    )

  def test_get_set_night_light_temperature(self):
    night_light_temperature = 7000
    logging.info(
        'Setting night light temperature to %s', night_light_temperature
    )
    self.display.set_night_light_temperature(night_light_temperature)
    asserts.assert_equal(
        self.display.get_night_light_temperature(),
        night_light_temperature,
        'Night light temperature is not set correctly.',
    )

    new_night_light_temperature = 5000
    logging.info(
        'Setting night light temperature to %s', new_night_light_temperature
    )
    self.display.set_night_light_temperature(new_night_light_temperature)
    asserts.assert_equal(
        self.display.get_night_light_temperature(),
        new_night_light_temperature,
        'Night light temperature is not set correctly.',
    )

  def test_get_set_mirror_mode(self):
    external_display_id = self._plug_in_external_display()
    logging.info('External display ID: %s', external_display_id)

    mirror_mode_enabled = self.display.get_mirror_mode()
    logging.info('Mirror mode is enabled: %s', mirror_mode_enabled)

    logging.info('Setting mirror mode to %s', not mirror_mode_enabled)
    self.display.set_mirror_mode(not mirror_mode_enabled)
    asserts.assert_equal(
        self.display.get_mirror_mode(),
        not mirror_mode_enabled,
        'Mirror mode is not set correctly.',
    )

    logging.info('Setting mirror mode to %s', mirror_mode_enabled)
    self.display.set_mirror_mode(mirror_mode_enabled)
    asserts.assert_equal(
        self.display.get_mirror_mode(),
        mirror_mode_enabled,
        'Mirror mode is not set correctly.',
    )

  def _plug_in_external_display(self) -> pasit_display.PasitDisplay.DisplayId:
    """Plug in external display and return the external display ID."""
    internal_display_id = self.helper.get_internal_display_id()
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_MONITOR)
    external_display_ids = self.helper.get_external_display_ids(
        internal_display_id, 1
    )
    return external_display_ids[0]


if __name__ == '__main__':
  test_runner.main()
