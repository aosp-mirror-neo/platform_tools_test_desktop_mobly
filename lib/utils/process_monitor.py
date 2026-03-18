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

"""Manages a process to start/restart it in the background, with monitoring."""

import atexit
import logging
import threading
import time
from typing import Callable

from lib.utils import managed_process
from mobly import logger as mobly_logger


class ProcessMonitor:
  """Monitors and manages a subprocess in a background daemon thread.

  This class wraps a `managed_process.ManagedProcess` object, ensuring the
  underlying command is kept running in the background. A dedicated daemon
  thread periodically checks if the process is running and restarts it if it has
  terminated, provided a device readiness condition is met.

  The watcher thread is daemonic, so it won't prevent the main program from
  exiting. Cleanup to stop the process and thread is registered to run at
  program exit.

  Attributes:
    log: LoggerAdapter instance for prefixed logging.
  """

  _WATCHER_THREAD_LOOP_INTERVAL_SECONDS = 1

  _process: managed_process.ManagedProcess
  _start_condition: Callable[[], bool]
  _watcher_thread: threading.Thread | None = None
  _cancel_event: threading.Event

  log: logging.LoggerAdapter  # pylint: disable=g-bare-generic

  def __init__(
      self,
      name: str,
      command: Callable[[], list[str]],
      start_condition: Callable[[], bool],
  ):
    """Initializes the ProcessMonitor.

    Args:
      name: The name for the process, used for logging and thread naming.
      command: A callable that returns the command and arguments to run as a
        subprocess.
      start_condition: A callable that returns True if conditions are met to
        start/restart the process (e.g., device is ready), False otherwise.
    """
    self._process = managed_process.ManagedProcess(name, command)
    self._start_condition = start_condition
    self._watcher_thread = None
    self._cancel_event = threading.Event()
    self._name = name
    self.log = mobly_logger.PrefixLoggerAdapter(
        logging.getLogger(),
        {
            mobly_logger.PrefixLoggerAdapter.EXTRA_KEY_LOG_PREFIX: (
                f'[{self._name}]'
            )
        },
    )
    atexit.register(self._cleanup)

  def start(self) -> None:
    """Starts the background watcher thread to monitor and run the process.

    If the watcher thread is already running, this method logs a warning
    and does nothing. The watcher thread is responsible for calling
    the underlying process's start() method.
    """
    # if watcher thread exists, then the process is assumed to be started
    # because the thread keeps restarting the process if it is terminated.
    if self._watcher_thread:
      self.log.warning('Watcher thread is already started.')
      return

    # create the watcher thread to maintain the process
    self.log.debug('Starting watcher thread...')
    self._cancel_event.clear()
    # watcher thread will start the process and restart it if
    # it is terminated.
    self._watcher_thread = threading.Thread(
        target=self._watch,
        args=[],
        # make sure the thread is not blocking the main/test process termination
        daemon=True,
        name=f'{self._name}_watcher_thread',
    )
    self._watcher_thread.start()

  def stop(self) -> None:
    """Signals the watcher thread to stop and waits for it to join.

    This will also result in stopping the underlying subprocess.
    """
    self.log.debug('Stopping watcher thread...')
    self._cancel_and_join_watcher_thread()

  def _cleanup(self) -> None:
    """Cleans up resources by stopping the watcher thread at exit."""
    self.log.info('Cleaning up watcher thread...')
    self._cancel_and_join_watcher_thread()

  def _cancel_and_join_watcher_thread(self) -> None:
    """Sets the cancel event and joins the watcher thread."""
    self._cancel_event.set()
    if self._watcher_thread:
      self.log.debug('Joining watcher thread...')
      self._watcher_thread.join()
      self.log.debug('Watcher thread joined.')
      self._watcher_thread = None

  def _watch(self) -> None:
    """The main loop for the watcher thread.

    Continuously checks if the subprocess needs to be started/restarted,
    based on the `_start_condition` condition, until the cancel event is set.
    The underlying process is stopped upon exiting this loop.
    """
    try:
      # check if the cancel event is set - if it is set, exit the loop and stop
      # the process.
      while not self._cancel_event.is_set():
        if not self._process.is_running():
          # check if the start condition is met before restarting the process
          if self._start_condition():
            self._process.start()
          else:
            self.log.debug('Start condition is not met.')
        time.sleep(self._WATCHER_THREAD_LOOP_INTERVAL_SECONDS)
      self.log.debug('Watcher is cancelled.')
    except Exception as e:  # pylint: disable=broad-except
      self.log.warning('Watcher thread is interrupted: %s', e)
    finally:
      self._process.stop()
