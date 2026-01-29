# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A wrapper for Mobly tests that are invoked via Tradefed.
"""

import argparse
import functools
import logging
import os
import sys
from typing import Any, Callable

from mobly import config_parser


def _log_imported_modules_with_paths():
  """Logs all imported modules and their associated file paths."""
  logging.debug('Listing imported modules and their paths:')
  for module_name, module_obj in sorted(sys.modules.items()):
    if module_obj is not None:
      try:
        file_path = getattr(module_obj, '__file__', None)
        if file_path:
          abs_path = os.path.abspath(file_path)
          logging.debug('%s: %s', module_name, abs_path)
        else:
          logging.debug('%s: [Built-in or no file]', module_name)
      except Exception as e:  # pylint: disable=broad-exception-caught
        logging.debug('%s: [Error accessing path: %s]', module_name, e)
    else:
      logging.debug('%s: [Module object is None]', module_name)


def wrap_tradefed_args(func: Callable[..., Any]) -> Callable[..., Any]:
  """A decorator that wraps a Mobly main function.

  This wrapper is an intermediate for Mobly tests that are invoked via
  Tradefed's MoblyBinaryHostTest harness. This harness does not use the
  standard Mobly command line conventions. This wrapper extracts the
  log_path from the command line and sets the required environment
  variable.

  Args:
    func: The function to wrap.

  Returns:
    The wrapped function.
  """

  @functools.wraps(func)
  def wrapper(*args, **kwargs):
    # Handle options before '--' (none at the moment).
    if '--' in sys.argv:
      index = sys.argv.index('--')
      sys.argv = sys.argv[:index] + sys.argv[index + 1:]

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--log_path', type=str, default=None)
    parsed_args, _ = parser.parse_known_args(sys.argv[1:])

    # Configure log path
    if parsed_args.log_path:
      os.environ[config_parser.ENV_MOBLY_LOGPATH] = parsed_args.log_path

    try:
      func(*args, **kwargs)
    finally:
      # Log all imported modules and their paths to help identify potential
      # conflicts.
      _log_imported_modules_with_paths()

  return wrapper
