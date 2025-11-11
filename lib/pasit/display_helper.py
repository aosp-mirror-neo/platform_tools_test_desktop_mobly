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

    Stable display IDs are display IDs that have been observed to be stable for
    a short period of time. This function waits for a short period of time and
    returns the display IDs if they are stable.

    Raises:
      DisplayIDsNotStableError: If the display IDs are not stable after a short
      delay.
    """
    display_ids = retry.retry(
        self._get_stable_ids,
        exceptions=(DisplayIDsNotStableError),
        policy=test_policy.DisplayTestPolicy.EXPECTED_DISPLAY_COUNT_RETRY_POLICY,
    )
    return display_ids

  def get_internal_display_id(self) -> pasit_display.PasitDisplay.DisplayId:
    """Returns the internal display ID.

    This function assumes that there is only one display plugged in.

    Raises:
      UnexpectedDisplayCountError: If the DUT has more than one display plugged
      in.
    """
    display_ids = retry.retry(
        self.display.get_display_ids,
        until=lambda display_ids: len(display_ids) == 1,
        policy=test_policy.DisplayTestPolicy.EXPECTED_DISPLAY_COUNT_RETRY_POLICY,
    )
    if len(display_ids) > 1:
      raise UnexpectedDisplayCountError(
          'This method should be called when there is only one display'
          ' plugged in.'
      )
    logging.debug('Internal display id: %s', display_ids[0])
    return display_ids[0]

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
        exceptions=(DisplayIDsNotStableError),
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

  def _get_stable_ids(self) -> list[pasit_display.PasitDisplay.DisplayId]:
    """Returns display IDs if stable, otherwise Raises DisplayIDsNotStableError."""
    initial_display_ids = self.display.get_display_ids()
    time.sleep(
        test_policy.DisplayTestPolicy.WAIT_FOR_IDS_TO_STABILIZE_DELAY_SECONDS
    )
    final_display_ids = self.display.get_display_ids()
    logging.debug('Initial display ids: %s', initial_display_ids)
    logging.debug('Final display ids: %s', final_display_ids)
    if set(initial_display_ids) == set(final_display_ids):
      return final_display_ids
    if len(initial_display_ids) == len(final_display_ids):
      # Even though we have a workaround for this, it is still a DUT bug and we
      # should be sure to surface the error and not hide it as a DEBUG only
      # message.  We will however only log the error if the count is the same
      # so as not to catch waiting for displays to connect/disconnect.
      logging.error(
          'Display IDs changed during stability check. Initial: %s, Final: %s',
          initial_display_ids,
          final_display_ids,
      )
    raise DisplayIDsNotStableError(
        'Display IDs changed during stability check. Initial:'
        f' {initial_display_ids}, Final: {final_display_ids}'
    )
