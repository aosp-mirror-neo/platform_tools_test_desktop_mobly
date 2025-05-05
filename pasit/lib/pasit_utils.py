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

"""Utility functions for PASIT testing.

Various utility functions and helpers for PASIT testing.
"""

from collections.abc import Callable
import logging
import time
from typing import Any


def retry_function(
    logger: logging.Logger,
    func: Callable[..., Any],
    func_args: tuple[Any, ...] | None = None,
    func_kwargs: dict[str, Any] | None = None,
    max_tries: int = 3,
    delay_seconds: int = 1,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Any:
  """A simple wrapper to retry another function.

  Args:
    logger: A logger to use for logging.
    func: The function to call and retry.
    func_args: A tuple of positional arguments to pass to func.
    func_kwargs: A dictionary of keyword arguments to pass to func.
    max_tries: Maximum number of times to retry.
    delay_seconds: Delay between retries in seconds.
    exceptions: A tuple of exception types to catch and retry on. Defaults to
      (Exception,).

  Returns:
    The result of the successfully called function.

  Raises:
    The last exception if all retries fail.
  """
  if func_args is None:
    func_args = ()
  if func_kwargs is None:
    func_kwargs = {}

  tries = 0
  while tries < max_tries:
    tries += 1
    try:
      return func(*func_args, **func_kwargs)
    except exceptions as e:
      if hasattr(func, '__name__'):
        func_name = func.__name__
      else:
        func_name = str(func)
      if tries >= max_tries:
        logger.error(
            f'"{func_name}" failed after {max_tries} tries with args'
            f' {func_args} and kwargs {func_kwargs}. Last exception: {e}'
        )
        raise
      logger.warning(
          f'"{func_name}" failed with {e} (args: {func_args}, kwargs:'
          f' {func_kwargs}). Retrying ({tries}/{max_tries}) in'
          f' {delay_seconds}s...'
      )
      time.sleep(delay_seconds)
