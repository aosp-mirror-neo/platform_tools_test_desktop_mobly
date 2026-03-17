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

"""Unit tests for retry.py."""

import unittest
from unittest import mock

from lib.utils import retry


def _throw_or_return_value(exception_type, return_value: int = 0) -> int:
  if exception_type is not None:
    raise exception_type("function failed")
  return return_value


class RetryTest(unittest.TestCase):

  def test_retry_succeeds_on_first_try(self):
    self.assertEqual(1, retry.retry(lambda: 1, policy=retry.RetryPolicy()))

  def test_retry_returns_none_if_max_tries_is_zero(self):
    self.assertIsNone(
        retry.retry(lambda: 1, policy=retry.RetryPolicy(max_tries=0))
    )

  def test_retry_raises_exception_if_max_tries_is_reached(self):
    exception_generator = (x for x in (Exception, TimeoutError, ValueError))
    with self.assertRaises(ValueError):
      retry.retry(
          lambda: _throw_or_return_value(next(exception_generator)),
          exceptions=(Exception,),
          policy=retry.RetryPolicy(max_tries=3),
      )

  def test_retry_returns_last_result_if_doesnt_throw_exception(self):
    exception_generator = (x for x in (TimeoutError, ValueError, None))
    self.assertEqual(
        4,
        retry.retry(
            lambda: _throw_or_return_value(next(exception_generator), 4),
            exceptions=(Exception,),
            policy=retry.RetryPolicy(max_tries=3),
        ),
    )

  def test_retry_raises_exception_if_not_listed_in_exceptions(self):
    exception_generator = (x for x in (ValueError, TimeoutError, None))
    with self.assertRaises(TimeoutError):
      retry.retry(
          lambda: _throw_or_return_value(next(exception_generator)),
          exceptions=(ValueError,),
          policy=retry.RetryPolicy(max_tries=3),
      )

  def test_retry_until_returns_5(self):
    func_result_generator = (x for x in range(10))
    self.assertEqual(
        5,
        retry.retry(
            lambda: next(func_result_generator),
            until=lambda x: x == 5,
            policy=retry.RetryPolicy(max_tries=10),
        ),
    )

  def test_retry_until_returns_5_returns_last_result(self):
    func_result_generator = (x for x in range(10))
    self.assertEqual(
        2,
        retry.retry(
            lambda: next(func_result_generator),
            until=lambda x: x == 5,
            policy=retry.RetryPolicy(max_tries=3),
        ),
    )


class MockTime:

  def __init__(self, start_time=1000.0):
    self._current_time = start_time

  def time(self) -> float:
    return self._current_time

  def sleep(self, duration: float):
    self._current_time += duration


class WaitForStableValueTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self.mock_time = MockTime()
    self.enterContext(mock.patch("time.time", side_effect=self.mock_time.time))
    self.enterContext(
        mock.patch("time.sleep", side_effect=self.mock_time.sleep)
    )

  def test_stabilizes_immediately(self):
    mock_func = mock.Mock(return_value="stable")
    result = retry.wait_for_stable_value(
        mock_func,
        timeout_seconds=10,
        delay_seconds=1,
        required_stable_duration_seconds=2,
    )
    self.assertEqual(result, "stable")
    # Initial call, then 2 calls within the loop to pass 2s stable time.
    self.assertEqual(mock_func.call_count, 3)

  def test_stabilizes_after_changes(self):
    mock_func = mock.Mock(side_effect=["A", "B", "C", "C", "C", "C", "C", "C"])
    mock_criteria = mock.Mock(
        side_effect=[True, False, True, False, True, True, True]
    )
    result = retry.wait_for_stable_value(
        mock_func,
        timeout_seconds=20,
        delay_seconds=1,
        required_stable_duration_seconds=3,
        criteria=mock_criteria,
    )
    self.assertEqual(result, "C")
    self.assertEqual(mock_func.call_count, 8)
    self.assertEqual(mock_criteria.call_count, 7)

  def test_stabilizes_but_criteria_never_met(self):
    mock_func = mock.Mock(side_effect=["A", "C", "A", "A", "A", "A", "A"])
    mock_criteria = mock.Mock(return_value=False)
    with self.assertRaises(retry.StabilizationTimeoutError) as context:
      retry.wait_for_stable_value(
          mock_func,
          timeout_seconds=5,
          delay_seconds=1,
          required_stable_duration_seconds=2,
          criteria=mock_criteria,
      )
    self.assertIn(
        "did not stabilize or meet the expected criteria within 5s",
        str(context.exception),
    )
    self.assertIn("A", str(context.exception))
    self.assertEqual(mock_func.call_count, 6)
    self.assertEqual(mock_criteria.call_count, 5)

  def test_timeout_if_never_stabilizes(self):
    values = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
    mock_func = mock.Mock(side_effect=values)
    with self.assertRaises(retry.StabilizationTimeoutError) as context:
      retry.wait_for_stable_value(
          mock_func,
          timeout_seconds=10,
          delay_seconds=1,
          required_stable_duration_seconds=2,
      )
    self.assertIn(
        "did not stabilize or meet the expected criteria within 10s",
        str(context.exception),
    )
    self.assertIn("K", str(context.exception))

  def test_timeout_if_not_stable_long_enough(self):
    mock_func = mock.Mock(
        side_effect=["A"] * 2 + ["B"] * 2 + ["C"] * 2 + ["D"] * 10
    )
    with self.assertRaises(retry.StabilizationTimeoutError):
      retry.wait_for_stable_value(
          mock_func,
          timeout_seconds=10,
          delay_seconds=1,
          required_stable_duration_seconds=5,
      )

  def test_zero_required_stability(self):
    mock_func = mock.Mock(return_value="any")
    result = retry.wait_for_stable_value(
        mock_func,
        timeout_seconds=5,
        delay_seconds=1,
        required_stable_duration_seconds=0,
    )
    self.assertEqual(result, "any")
    self.assertEqual(mock_func.call_count, 2)


if __name__ == "__main__":
  unittest.main()
