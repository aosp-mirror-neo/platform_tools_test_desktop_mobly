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

from lib.utils import retry


def _throw_or_return_value(exception_type, return_value: int = 0) -> int:
  if exception_type is not None:
    raise exception_type("function failed")
  return return_value


class RetryTest(unittest.TestCase):

  def test_retry_succeeds_on_first_try(self):
    self.assertEqual(1, retry.retry(lambda: 1))

  def test_retry_returns_none_if_max_tries_is_zero(self):
    self.assertIsNone(retry.retry(lambda: 1, max_tries=0))

  def test_retry_raises_exception_if_max_tries_is_reached(self):
    exception_generator = (x for x in (Exception, TimeoutError, ValueError))
    with self.assertRaises(ValueError):
      retry.retry(
          lambda: _throw_or_return_value(next(exception_generator)),
          exceptions=(Exception,),
          max_tries=3,
      )

  def test_retry_returns_last_result_if_doesnt_throw_exception(self):
    exception_generator = (x for x in (TimeoutError, ValueError, None))
    self.assertEqual(
        4,
        retry.retry(
            lambda: _throw_or_return_value(next(exception_generator), 4),
            exceptions=(Exception,),
            max_tries=3,
        ),
    )

  def test_retry_raises_exception_if_not_listed_in_exceptions(self):
    exception_generator = (x for x in (ValueError, TimeoutError, None))
    with self.assertRaises(TimeoutError):
      retry.retry(
          lambda: _throw_or_return_value(next(exception_generator)),
          exceptions=(ValueError,),
          max_tries=3,
      )

  def test_retry_until_returns_5(self):
    func_result_generator = (x for x in range(10))
    self.assertEqual(
        5,
        retry.retry(
            lambda: next(func_result_generator),
            until=lambda x: x == 5,
            max_tries=10,
        ),
    )

  def test_retry_until_returns_5_returns_last_result(self):
    func_result_generator = (x for x in range(10))
    self.assertEqual(
        2,
        retry.retry(
            lambda: next(func_result_generator),
            until=lambda x: x == 5,
            max_tries=3,
        ),
    )


if __name__ == "__main__":
  unittest.main()
