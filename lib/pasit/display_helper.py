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

from lib.pasit import pasit_display
from lib.pasit import test_policy
from lib.utils import retry


class UnexpectedDisplayCountError(Exception):
  """Error when the number of displays detected is unexpected."""


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
    the known internal display ID.

    Args:
      internal_display_id: The ID of the internal display to filter out.
      expected_external_display_count: The number of external displays expected.

    Returns:
      A list of external display IDs.

    Raises:
      UnexpectedDisplayCountError: If the final number of total or external
      displays does not match the expected counts after the timeout.
    """
    expected_total_display_count = expected_external_display_count + 1
    display_ids = retry.retry(
        self.display.get_display_ids,
        until=lambda ids: len(ids) == expected_total_display_count,
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
