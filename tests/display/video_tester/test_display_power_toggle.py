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

"""Testing the display power toggle functionality."""

import contextlib
import logging
import time
from typing import Generator

from display.utils import modetest_helper
from lib.pasit.passport import passport_host
from mobly import asserts
from mobly import base_suite
from mobly import config_parser
from mobly import suite_runner

from . import display_on_off_base


class DisplayPowerToggleTest(display_on_off_base.DisplayOnOffBase):
  """Test class for testing the display power toggle functionality."""

  def __init__(
      self,
      configs: config_parser.TestRunConfig,
      enable_stress_tests: bool = False,
  ):
    super().__init__(configs, enable_stress_tests=enable_stress_tests)

  def setup_class(self):
    """Sets up the class and performs a pre-check on power toggle."""
    super().setup_class()
    self._precheck_hwc_display_power_toggle()

  @property
  def power_off_verb(self) -> str:
    return 'display-power-off'

  @property
  def power_on_verb(self) -> str:
    return 'display-power-reset'

  @contextlib.contextmanager
  def power_cycle_displays(self) -> Generator[None, None, None]:
    """A context manager to power off and on the displays."""
    display_ids = self.display.get_display_ids()

    for display_id in display_ids:
      logging.info('Turning off display_id: %s', display_id)
      self.dut.shell(['cmd', 'display', 'power-off', display_id.id])

    # This creates a context manager for use with a `with` statement.
    # The `try...yield...finally` ensures that the displays are always
    # powered back on in the `finally` block, even if the code inside the
    # `with` block (which runs at `yield`) raises an exception.
    try:
      yield
    finally:
      for display_id in display_ids:
        logging.info('Turning on display_id: %s', display_id)
        self.dut.shell(['cmd', 'display', 'power-reset', display_id.id])

  def _precheck_hwc_display_power_toggle(self):
    """Performs a pre-check that the HWC is properly toggles the display power."""
    logging.debug('Performing pre-test check for display power toggle.')

    # 1. Check initial state is valid.
    # Assert no external displays are connected.
    asserts.assert_true(
        self._ucd_manager.wait_for_display_count(0),
        'Pre-check expects no external displays to be connected.',
    )

    (
        _,
        initial_connectors_by_id,
    ) = modetest_helper.get_all_connectors_props(self.dut)

    # Find the single connected internal display.
    connected_connectors = [
        (cid, cprops)
        for cid, cprops in initial_connectors_by_id.items()
        if cprops['connected']
    ]

    asserts.assert_equal(
        len(connected_connectors),
        1,
        'Pre-check failed: Expected exactly one connected display, but found '
        f'{len(connected_connectors)}.',
    )

    connector_id, connector = connected_connectors[0]
    initial_active_encoder = connector['active_encoder']
    asserts.assert_not_equal(
        initial_active_encoder,
        0,
        'Pre-check failed: Internal display has no active encoder before '
        'power-off.',
    )

    _, initial_encoders = modetest_helper.get_all_encoders_props(self.dut)
    asserts.assert_in(
        initial_active_encoder,
        initial_encoders,
        f"Pre-check failed: Active encoder '{initial_active_encoder}' not"
        ' found.',
    )
    initial_crtc = initial_encoders[initial_active_encoder]['crtc']
    asserts.assert_not_equal(
        initial_crtc,
        0,
        'Pre-check failed: Encoder has no CRTC attached before power-off.',
    )

    # 2. Power off and check state.
    display_id_obj = self.internal_display_id
    self.dut.shell(['cmd', 'display', 'power-off', str(display_id_obj)])
    time.sleep(5)  # Give time for the state to update.
    _, off_connectors_by_id = modetest_helper.get_all_connectors_props(self.dut)
    _, off_encoders = modetest_helper.get_all_encoders_props(self.dut)
    off_active_encoder = off_connectors_by_id[connector_id]['active_encoder']
    off_crtc = off_encoders[initial_active_encoder]['crtc']
    asserts.assert_equal(
        off_active_encoder,
        0,
        'Pre-check failed: Active encoder was not 0 after power-off.',
    )
    asserts.assert_equal(
        off_crtc,
        0,
        'Pre-check failed: CRTC for encoder was not 0 after power-off.',
    )

    # 3. Power on and check state.
    self.dut.shell(['cmd', 'display', 'power-reset', str(display_id_obj)])
    time.sleep(5)
    (
        _,
        reset_connectors_by_id,
    ) = modetest_helper.get_all_connectors_props(self.dut)
    _, reset_encoders = modetest_helper.get_all_encoders_props(self.dut)
    reset_active_encoder = reset_connectors_by_id[connector_id][
        'active_encoder'
    ]
    reset_crtc = reset_encoders[initial_active_encoder]['crtc']
    asserts.assert_equal(
        reset_active_encoder,
        initial_active_encoder,
        'Pre-check failed: Active encoder did not reset correctly.',
    )
    asserts.assert_equal(
        reset_crtc,
        initial_crtc,
        'Pre-check failed: CRTC for encoder did not reset correctly.',
    )

    logging.debug('Pre-test check for display power toggle passed.')


class DisplayPowerToggleTestSuite(base_suite.BaseSuite):
  """Test suite for testing the display power toggle functionality."""

  def setup_suite(self, config: config_parser.TestRunConfig):
    passport_host.update_passport_host_config(config)

    self.add_test_class(DisplayPowerToggleTest, config)


def main() -> None:
  suite_runner.run_suite_class()


if __name__ == '__main__':
  main()
