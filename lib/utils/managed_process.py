# Copyright 2026 Google LLC
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

"""Utilities for managing and controlling external subprocesses.

This module contains the ManagedProcess class, designed to simplify the
lifecycle management of commands run via subprocess.Popen. It allows starting,
stopping, restarting, and checking the status of an external process,
with integrated logging.
"""

import logging
import subprocess
from typing import Callable

from mobly import logger as mobly_logger
from mobly import utils as mobly_utils


class ManagedProcess:
  """Manages the lifecycle of a single external command subprocess.

  This class wraps `subprocess.Popen` to provide a higher-level interface
  for controlling an external command. Instances of this class represent
  a potentially long-running process, offering methods to start (or restart),
  stop, and check its running status.

  Key features include:
    - Restart: The `start()` method will restart the process if it
      has terminated.
    - Shutdown: The `stop()` method gracefully stops the process.
    - Prefixed logging: All logs related to this process instance are
      automatically prefixed with the process name.

  Note: This class is not thread-safe. External synchronization is required
  if an instance is accessed from multiple threads.

  Attributes:
    log: The logger adapter instance used for logging, prefixed with the process
      name.
  """

  _name: str
  _command: Callable[[], list[str]]
  _process: subprocess.Popen[bytes] | None = None

  log: logging.LoggerAdapter  # pylint: disable=g-bare-generic

  def __init__(self, name: str, command: Callable[[], list[str]]):
    """Initializes the ManagedProcess instance.

    Args:
      name: A string identifier for this process, used primarily for logging.
      command: A callable that returns a list of strings representing the
        command and its arguments to be executed (as passed to
        `subprocess.Popen`).
    """
    self._name = name
    # Note:the command should be a callable so that any timestamps in the
    # command are updated each time the process is started.
    self._command = command
    self._process = None
    self.log = mobly_logger.PrefixLoggerAdapter(
        logging.getLogger(),
        {
            mobly_logger.PrefixLoggerAdapter.EXTRA_KEY_LOG_PREFIX: (
                f'[{self._name}]'
            )
        },
    )

  def is_running(self) -> bool:
    """Checks if the subprocess is currently running.

    Returns:
      True if the process is running (has been started and not yet
      terminated), False otherwise.
    """
    return self._process is not None and self._process.poll() is None

  def stop(self) -> None:
    """Stops the running subprocess.

    If the process is not running, this method does nothing.
    """
    self._stop()

  def start(self) -> None:
    """Starts or restarts the external command as a subprocess.

    If the process has never been started, it's started. If the process was
    started but has since terminated, it's restarted. If the process is
    currently running, this method does nothing.
    """
    if self._process is None:
      self._process = self._start()
    else:
      return_code = self._process.poll()
      if return_code is not None:
        stdout = self._process.stdout
        stderr = self._process.stderr
        self.log.debug(
            'The process terminated with return code %d (stdout:'
            ' "%s", stderr: "%s"), restarting...',
            return_code,
            stdout.read().decode('utf-8', errors='replace') if stdout else '',
            stderr.read().decode('utf-8', errors='replace') if stderr else '',
        )
        self._process = self._start()

  def _start(self) -> subprocess.Popen[bytes]:
    """Handles the actual execution of the subprocess.

    Returns:
      A subprocess.Popen object representing the started process.
    """
    self.log.info('Starting the process...')
    return mobly_utils.start_standing_subprocess(
        self._command(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

  def _stop(self) -> None:
    """Implements the logic to stop the subprocess."""
    if not self._process:
      self.log.debug('Process is not running.')
      return
    self.log.info('Terminating the process...')
    mobly_utils.stop_standing_subprocess(self._process)
    self._process = None
