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
import time

from lib.pasit import pasit_display
from lib.pasit import test_policy
from lib.utils import retry


class UnexpectedDisplayCountError(Exception):
  """Error when the number of displays detected is unexpected."""


class DisplayIDsNotStableError(Exception):
  """Error when the display ID is not stable."""


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

  def get_stable_display_ids(
      self,
  ) -> list[pasit_display.PasitDisplay.DisplayId]:
    """Returns a list of stable display IDs.

    This function polls for the display IDs until they have been stable for a
    configured duration.

    Raises:
      DisplayIDsNotStableError: If the display IDs do not stabilize within the
      configured timeout.
    """
    return self._get_stable_ids()

  def get_internal_display_id(self) -> pasit_display.PasitDisplay.DisplayId:
    """Returns the internal display ID."""

    return self.display.get_internal_display_id()

  def get_external_display_ids(
      self,
      internal_display_id: pasit_display.PasitDisplay.DisplayId,
      expected_external_display_count: int,
  ) -> list[pasit_display.PasitDisplay.DisplayId]:
    """Waits for and returns the external display IDs.

    This function calculates the total expected displays (external + 1 internal)
    and waits until that number of displays is detected. It then filters out
    the known internal display ID.  It also ensures the display IDs are stable.

    Args:
      internal_display_id: The ID of the internal display to filter out.
      expected_external_display_count: The number of external displays expected.

    Returns:
      A list of external display IDs.

    Raises:
      UnexpectedDisplayCountError: If the final number of total or external
      displays does not match the expected counts after the timeout.
      DisplayIDsNotStableError: If the display IDs are not stable this error
      will be raised.
    """
    expected_total_display_count = expected_external_display_count + 1
    display_ids = retry.retry(
        self._get_stable_ids,
        until=lambda ids: len(ids) == expected_total_display_count,
        exceptions=(DisplayIDsNotStableError,),
        policy=test_policy.DisplayTestPolicy.EXPECTED_DISPLAY_COUNT_RETRY_POLICY,
    )
    if len(display_ids) != expected_total_display_count:
      raise UnexpectedDisplayCountError(
          f'Expected {expected_total_display_count} displays, but got'
          f' {len(display_ids)}'
      )
    external_display_ids = [
        display_id
        for display_id in display_ids
        if display_id != internal_display_id
    ]
    if len(external_display_ids) != expected_external_display_count:
      raise UnexpectedDisplayCountError(
          f'Expected {expected_external_display_count} external displays, but'
          f' got {len(external_display_ids)}'
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

  def get_display_count(
      self,
      expected_display_count: int,
      expected_off: list[pasit_display.PasitDisplay.DisplayId] | None = None,
  ) -> int:
    """Returns the number of displays detected.

    The function waits for the display IDs to be stable and returns the number
    of displays. This will retry according to the retry policy if the display
    count does not match the expected count. The will return the last stable
    display count, even if it is not the expected count.  It will also ensure
    that the displays are in the expected state (ON or OFF) based on the
    expected_off list.

    Args:
      expected_display_count: The expected number of displays.
      expected_off: A list of display IDs expected to be OFF. All other detected
        displays are expected to be ON.

    Returns:
      The number of displays detected.

    Raises:
      DisplayIDsNotStableError: If the display IDs are not stable this error
      will be raised.
      DisplayStateMismatchError: If the displays are not in the expected state,
        all displays are expected to be ON except for the ones in expected_off.
    """
    display_ids = retry.retry(
        self._get_stable_ids,
        until=lambda display_ids: len(display_ids) == expected_display_count,
        exceptions=(DisplayIDsNotStableError,),
        policy=test_policy.DisplayTestPolicy.EXPECTED_DISPLAY_COUNT_RETRY_POLICY,
    )
    self._wait_for_displays_on(display_ids, expected_off)
    return len(display_ids)

  def _get_stable_ids(self) -> list[pasit_display.PasitDisplay.DisplayId]:
    """Returns display IDs if stable, otherwise Raises DisplayIDsNotStableError."""
    start_time = time.time()
    last_display_ids = self.display.get_display_ids()
    stable_start_time = start_time
    logging.debug('Waiting for display IDs to stabilize...')

    while (
        time.time() - start_time
        < test_policy.DisplayTestPolicy.STABLE_ID_TIMEOUT_SECONDS
    ):
      time.sleep(
          test_policy.DisplayTestPolicy.STABLE_ID_POLLING_INTERVAL_SECONDS
      )
      current_display_ids = self.display.get_display_ids()
      logging.debug(
          'Polling for stable display IDs. Current: %s, Last: %s',
          current_display_ids,
          last_display_ids,
      )

      if set(current_display_ids) == set(last_display_ids):
        if (
            time.time() - stable_start_time
            >= test_policy.DisplayTestPolicy.STABLE_ID_REQUIRED_DURATION_SECONDS
        ):
          logging.debug(
              'Display IDs have been stable for %ds: %s',
              test_policy.DisplayTestPolicy.STABLE_ID_REQUIRED_DURATION_SECONDS,
              current_display_ids,
          )
          return current_display_ids
      else:
        if len(last_display_ids) == len(current_display_ids):
          # Even though we have a workaround for this, it is still a DUT bug and
          # we should be sure to surface the error and not hide it as a DEBUG
          # only message.  We will however only log the error if the count is
          # the same so as not to catch waiting for displays to
          # connect/disconnect.
          logging.error(
              'Display IDs changed during stability check. Last: %s,'
              ' Current: %s',
              last_display_ids,
              current_display_ids,
          )
        last_display_ids = current_display_ids
        stable_start_time = time.time()

    raise DisplayIDsNotStableError(
        'Display IDs did not stabilize within'
        f' {test_policy.DisplayTestPolicy.STABLE_ID_TIMEOUT_SECONDS}s. Last'
        f' seen IDs: {last_display_ids}'
    )
