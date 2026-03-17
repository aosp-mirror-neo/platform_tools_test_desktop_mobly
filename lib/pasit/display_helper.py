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
from typing import Callable

from lib.pasit import pasit_display
from lib.pasit import test_policy
from lib.utils import retry


class DisplayStateMismatchError(Exception):
  """Error when the display state is not as expected."""


class DisplayHelper:
  """Helper class for display testing tools for PASIT tests.

  Attributes:
    display: The display to use for the display tools.
  """

  display: pasit_display.PasitDisplay

  def __init__(
      self,
      display: pasit_display.PasitDisplay,
  ):
    """Initializes the display tools.

    Args:
      display: The display to use for the display tools.
    """
    self.display = display

  def get_internal_display_id(self) -> pasit_display.PasitDisplay.DisplayId:
    """Returns the internal display ID."""

    return self.display.get_internal_display_id()

  def get_external_display_ids(
      self,
      expected_external_display_count: int,
  ) -> list[pasit_display.PasitDisplay.DisplayId]:
    """Waits for and returns the external display IDs.

    This function waits until the expected number of external displays is
    detected and ensures the display IDs are stable.

    Args:
      expected_external_display_count: The number of external displays expected.

    Returns:
      A list of external display IDs.

    Raises:
      StabilizationTimeoutError: If the display IDs are not stable or the
      expected number of displays are not detected.
    """
    external_display_ids = self._get_stable_ids(
        self.display.get_external_display_ids, expected_external_display_count
    )
    logging.debug('External display ids: %s', external_display_ids)
    return external_display_ids

  def _wait_for_displays_on(
      self,
      display_ids: list[pasit_display.PasitDisplay.DisplayId],
      expected_off: list[pasit_display.PasitDisplay.DisplayId] | None = None,
  ) -> None:
    """Waits for the displays to be in the expected state.

    Args:
      display_ids: The list of display IDs to check.
      expected_off: A list of display IDs expected to be Off. All other displays
        are expected to be On.

    Returns:
      None
    Raises:
      DisplayStateMismatchError: If the displays are not in the expected state,
        all displays are expected to be On except for the ones in expected_off.
    """
    expected_off = expected_off or []

    def _state_to_string(state: bool) -> str:
      return 'On' if state else 'Off'

    def _check_displays_on() -> None:
      mismatches = []
      for display_id in display_ids:
        is_on = self.display.is_display_on(display_id)
        expected_on = not any(
            display_id.is_same_physical_display(expected_off_id)
            for expected_off_id in expected_off
        )
        if is_on != expected_on:
          mismatches.append(
              f'Display {display_id!r} is {_state_to_string(is_on)}, but'
              f' expected {_state_to_string(expected_on)}.'
          )

      if mismatches:
        raise DisplayStateMismatchError(' '.join(mismatches))

    retry.retry(
        _check_displays_on,
        exceptions=(DisplayStateMismatchError,),
        policy=test_policy.DisplayTestPolicy.EXPECTED_DISPLAY_COUNT_RETRY_POLICY,
    )

  def is_display_setup_correct(
      self,
      expected_display_count: int,
      expected_off: list[pasit_display.PasitDisplay.DisplayId] | None = None,
  ) -> tuple[bool, str | None]:
    """Verifies the display count and states after stabilization.

    This method waits for the set of detected display IDs to become stable.
    It then checks if the count of stable displays matches
    `expected_display_count`. Finally, it verifies that all detected
    displays are ON, except for those specified in the `expected_off` set.

    Internal timeouts or state mismatches result in False.

    Args:
      expected_display_count: The exact number of displays expected to be
        detected and stable.
      expected_off: A collection of display IDs that are expected to be in the
        OFF state. All other displays found are expected to be ON. If None or
        empty, all detected displays must be ON.

    Returns:
      A tuple of (bool, str | None).
      The first element is True if the display count and states match the
      expectations after stabilization, False otherwise.
      The second element is the error message if the display count or states do
      not match the expectations after stabilization, None otherwise.
    """
    try:
      display_ids = self._get_stable_ids(
          self.display.get_display_ids, expected_display_count
      )
    except retry.StabilizationTimeoutError as e:
      return (
          False,
          (
              'Failed to get stable display IDs or display count not equal to '
              f'expected ({expected_display_count}): {e}'
          ),
      )
    try:
      self._wait_for_displays_on(display_ids, expected_off)
    except DisplayStateMismatchError as e:
      return (False, f'Display state mismatch: {e}')
    return (True, None)

  def _get_stable_ids(
      self,
      get_display_ids_func: Callable[
          [], list[pasit_display.PasitDisplay.DisplayId]
      ],
      expected_display_count: int,
  ) -> list[pasit_display.PasitDisplay.DisplayId]:
    """Returns display IDs if stable, otherwise raises an error."""
    # TODO: b/491864518 - Replace this with retry with
    # EXPECTED_DISPLAY_COUNT_RETRY_POLICY once the bug is fixed.
    return retry.wait_for_stable_value(
        get_display_ids_func,
        timeout_seconds=test_policy.DisplayTestPolicy.STABLE_ID_TIMEOUT_SECONDS,
        delay_seconds=test_policy.DisplayTestPolicy.STABLE_ID_POLLING_INTERVAL_SECONDS,
        required_stable_duration_seconds=test_policy.DisplayTestPolicy.STABLE_ID_REQUIRED_DURATION_SECONDS,
        criteria=lambda ids: len(ids) == expected_display_count,
        value_name='display IDs',
    )
