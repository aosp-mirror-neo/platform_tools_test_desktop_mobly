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

"""Retry function for PASIT testing.

This module provides a retry function that can be used to call a function and
retry it if it fails. The retry function can be used to call a function that
may fail due to transient errors, such as timeouts or exceptions.
"""

from collections.abc import Callable
import logging
import math
import time
from typing import Optional, Tuple, TypeVar


_T = TypeVar('_T')


class RetryPolicy:
  """Policy for retrying a function.

  Attributes:
    max_tries: Maximum number of times to retry. Defaults to 3.
    delay_seconds: Delay between retries in seconds. Defaults to 1.
  """

  max_tries: int
  delay_seconds: int

  def __init__(self, max_tries: int = 3, delay_seconds: int = 1):
    self.max_tries = max_tries
    self.delay_seconds = delay_seconds


def retry(
    func: Callable[[], _T],
    policy: RetryPolicy,
    until: Callable[[_T], bool] = lambda _: True,
    exceptions: tuple[type[BaseException], ...] = (),
) -> _T:
  """A simple wrapper to retry another function.

  The function will retry until:
    - the until predicate is met, AND
    - the listed exceptions are not raised anymore.
  The number of retries is limited by max_tries.

  Either until or exceptions should be specified, otherwise the function will
  never retry.

  To retry on exceptions, use the exceptions argument. For example:
  retry(lambda: call_rpc_with_params(1, 2), exceptions=(RpcError, TimeoutError))

  To retry until a condition is met, use the until argument. For example:
  retry(is_device_online, until=lambda is_online: is_online)

  Args:
    func: The function to call and retry.
    until: A predicate that takes the result of func call and returns True if
      the function func should not be retried. Defaults to lambda _: True.
    policy: The policy for the retry function.
    exceptions: A tuple of exception types to catch and retry on.

  Returns:
    The result of the function if it succeeds or the last result if all retries
    fail.

  Raises:
    The last exception if all retries fail.
  """
  tries = 0
  while tries < policy.max_tries:
    tries += 1
    try_result, func_result = _try_function(
        func, tries, policy.max_tries, exceptions
    )
    # If the function was successful and the 'until' predicate is met,
    # return the result.
    if try_result and until(func_result):
      return func_result

    if tries >= policy.max_tries:
      logging.debug('Retry failed after %d attempts.', policy.max_tries)
      return func_result

    # If the function failed or did not meet the exit predicate, log the error
    # and sleep for the delay.
    logging.debug(
        'Attempt %d/%d failed. Retrying in %ds...',
        tries,
        policy.max_tries,
        policy.delay_seconds,
    )
    time.sleep(policy.delay_seconds)


def _try_function(
    func: Callable[[], _T],
    current_try: int,
    max_tries: int,
    exceptions: tuple[type[BaseException], ...] = (),
) -> Tuple[bool, Optional[_T]]:
  """Calls a function wrapped in a try/except block.

  Logic for retrying a function with a try/except block. This function is
  intended to be used by the retry function to call a function and retry it if
  it fails.

  Args:
    func: The function to call.
    current_try: The current try number.
    max_tries: The maximum number of times the function can be tried.
    exceptions: A tuple of exception types to catch and retry on.

  Raises:
    The exception if the function fails and the current try is equal to
    max_tries.

  Returns:
    A tuple of (bool, Optional[_T]) where the bool indicates whether the
    function was successful and the Optional[_T] is the result of the function
    if successful, otherwise None.
  """
  try:
    # No exceptions are raised, so the function is successful
    return (True, func())
  except exceptions as e:
    logging.debug('Exception caught: %s', e)
    if current_try < max_tries:
      # The function failed, but there are more tries, so return (False, None)
      return (False, None)
    else:
      logging.debug(
          'Retry failed after %d attempts. Last exception: %s',
          max_tries,
          e,
          exc_info=True,
      )
      raise


class StabilizationTimeoutError(Exception):
  """Error raised when a value does not stabilize within the timeout."""


def wait_for_stable_value(
    func: Callable[[], _T],
    timeout_seconds: int,
    delay_seconds: int,
    required_stable_duration_seconds: int,
    criteria: Callable[[_T], bool] = lambda _: True,
    value_name: str = 'value',
) -> _T | None:
  """Polls a function until its return value remains unchanged for a duration.

  This function repeatedly calls `func` every `delay_seconds`, checking if the
  returned value has been the same for at least
  `required_stable_duration_seconds`. The process continues until the value
  stabilizes or the total time elapsed exceeds `timeout_seconds`.

  Args:
    func: A callable that takes no arguments and returns a value to be checked
      for stability.
    timeout_seconds: The maximum total time to wait for the value to stabilize.
    delay_seconds: The time to wait between calls to `func`.
    required_stable_duration_seconds: The minimum duration the return value from
      `func` must remain constant to be considered stable.
    criteria: A callable that takes the return value of `func` and returns True
      if the value is considered stable. This criteria has to be met
      continuously for `required_stable_duration_seconds` for the function to
      return.
    value_name: The name of the value to be checked for stability. This is used
      for logging purposes only.

  Returns:
    The value returned by `func` once it has been stable for the required
    duration.

  Raises:
    StabilizationTimeoutError: If the return value of `func` does not stabilize
      within the specified `timeout_seconds`.
  """
  start_time = time.time()
  end_time = start_time + timeout_seconds

  last_result = func()
  stable_start_time = start_time
  logging.debug('Waiting for %s to stabilize...', value_name)

  while time.time() < end_time:
    time.sleep(delay_seconds)
    current_result = func()
    logging.debug(
        'Polling for stable %s. Current: %s, Last: %s',
        value_name,
        current_result,
        last_result,
    )

    if criteria(current_result) and current_result == last_result:
      time_since_last_change = time.time() - stable_start_time
      if (
          time_since_last_change > required_stable_duration_seconds
          or math.isclose(
              time_since_last_change, required_stable_duration_seconds
          )
      ):
        logging.debug(
            'The %s have been stable for %ds: %s',
            value_name,
            required_stable_duration_seconds,
            current_result,
        )
        return current_result
    else:
      logging.warning(
          'The %s changed or criteria not met during stability check. Last: %s,'
          ' Current: %s',
          value_name,
          last_result,
          current_result,
      )
      last_result = current_result
      stable_start_time = time.time()
  raise StabilizationTimeoutError(
      f'The {value_name} did not stabilize or meet the expected criteria within'
      f' {timeout_seconds}s. Last seen result: {last_result}',
  )
