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

"""Test changing external display resolutions with dock and dockless mode."""

import enum
import logging

from lib.pasit import pasit_display
from lib.pasit import peripheral_connector
from lib.pasit import test_policy
from lib.utils import functools
from lib.utils import retry
from mobly import asserts
from mobly import test_runner
from pasit.display import display_base_test


class ResolutionType(enum.Enum):
  LOWEST = 'lowest'
  MIDDLE = 'middle'
  HIGHEST = 'highest'


@functools.generate_tests
class ChangeDisplayResolutionTest(display_base_test.DisplayBaseTest):
  """Test changing external display resolutions with dock and dockless mode."""

  @functools.with_variants(
      one_display_dock=(peripheral_connector.ConnectionType.DOCK, 1),
      one_display_dockless=(peripheral_connector.ConnectionType.DOCKLESS, 1),
      two_displays_dock=(peripheral_connector.ConnectionType.DOCK, 2),
      two_displays_dockless=(peripheral_connector.ConnectionType.DOCKLESS, 2),
  )
  def test_external_display_resolution_when_dut(
      self,
      connection_type: peripheral_connector.ConnectionType,
      external_display_count: int,
  ):
    internal_display_id = self.helper.get_internal_display_id()
    self.plug_in_external_displays(external_display_count, connection_type)
    self.verify_display_count(
        external_display_count + 1,
        'after external displays plug in',
    )
    external_display_ids = self.helper.get_external_display_ids(
        internal_display_id, external_display_count
    )
    initial_resolutions, display_support_maps = self._get_initial_display_info(
        external_display_ids
    )
    for resolution_type in ResolutionType:
      logging.info('Testing %s resolutions', resolution_type.value)
      for display_id in external_display_ids:
        mode_id, target_resolution = self._get_representative_resolution(
            display_support_maps[display_id], resolution_type
        )
        logging.info('Setting display %s to %s', display_id, target_resolution)
        self.display.set_display_resolution(mode_id, display_id)
        self._verify_resolution(display_id, mode_id, target_resolution)
      self.capture_screenshots(
          f'Resolution_{resolution_type.value}_all_displays'
      )
    self._restore_initial_resolutions(initial_resolutions)

  def _get_initial_display_info(
      self, external_display_ids: list[pasit_display.PasitDisplay.DisplayId]
  ) -> tuple[
      dict[
          pasit_display.PasitDisplay.DisplayId,
          pasit_display.PasitDisplay.DisplayResolution,
      ],
      dict[
          pasit_display.PasitDisplay.DisplayId,
          dict[str, pasit_display.PasitDisplay.DisplayResolution],
      ],
  ]:
    initial_resolutions = {}
    display_support_maps = {}
    for display_id in external_display_ids:
      initial_resolutions[display_id] = self.display.get_display_resolution(
          display_id
      )
      display_support_maps[display_id] = (
          self.display.get_supported_display_resolutions(display_id)
      )
    return initial_resolutions, display_support_maps

  def _get_representative_resolution(
      self,
      support_map: dict[str, pasit_display.PasitDisplay.DisplayResolution],
      resolution_type: ResolutionType,
  ) -> tuple[str, pasit_display.PasitDisplay.DisplayResolution]:
    sorted_mode_ids = sorted(
        support_map.keys(),
        key=lambda mode_id: support_map[mode_id].width
        * support_map[mode_id].height,
    )
    asserts.assert_greater_equal(
        len(sorted_mode_ids),
        3,
        'Display support check failed: expected at least 3 resolutions, but '
        f'found only {len(sorted_mode_ids)} modes in the support map.',
    )
    if resolution_type == ResolutionType.LOWEST:
      target_mode_id = sorted_mode_ids[0]
    elif resolution_type == ResolutionType.MIDDLE:
      target_mode_id = sorted_mode_ids[len(sorted_mode_ids) // 2]
    else:
      target_mode_id = sorted_mode_ids[-1]
    return target_mode_id, support_map[target_mode_id]

  def _verify_resolution(
      self,
      display_id: pasit_display.PasitDisplay.DisplayId,
      mode_id: str,
      target_resolution: pasit_display.PasitDisplay.DisplayResolution,
  ) -> None:
    current_resolution_info = retry.retry(
        lambda: self.display.get_display_resolution(display_id),
        until=lambda info: info[0] == mode_id,
        policy=test_policy.DisplayTestPolicy.DISPLAY_RESOLUTION_CHANGED_RETRY_POLICY,
    )
    asserts.assert_equal(
        current_resolution_info,
        (mode_id, target_resolution),
        f'Display {display_id} failed to reach {target_resolution}',
    )

  def _restore_initial_resolutions(
      self,
      initial_resolutions: dict[
          pasit_display.PasitDisplay.DisplayId,
          dict[str, pasit_display.PasitDisplay.DisplayResolution],
      ],
  ) -> None:
    for display_id, resolution_info in initial_resolutions.items():
      logging.info(
          'Restoring display %s to initial mode %s (%s)',
          display_id,
          resolution_info[0],
          resolution_info[1],
      )
      self.display.set_display_resolution(resolution_info[0], display_id)


if __name__ == '__main__':
  test_runner.main()
