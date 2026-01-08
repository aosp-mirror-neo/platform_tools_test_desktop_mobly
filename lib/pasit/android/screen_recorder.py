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

"""Screen recorder for Android devices."""

import atexit
import logging
import os
import subprocess
import threading
import time
from mobly.controllers import android_device


_SCREEN_RECORDER_LOG_PREFIX = '[ScreenRecorder] '


def _log_warning(message: str, *args, **kwargs) -> None:
  logging.warning(_SCREEN_RECORDER_LOG_PREFIX + message, *args, **kwargs)


def _log_debug(message: str, *args, **kwargs) -> None:
  logging.debug(_SCREEN_RECORDER_LOG_PREFIX + message, *args, **kwargs)


def _log_info(message: str, *args, **kwargs) -> None:
  logging.info(_SCREEN_RECORDER_LOG_PREFIX + message, *args, **kwargs)


class ScreenRecordingProcess:
  """Manages process that runs 'adb shell screenrecord' command.

  Starts/restarts, stops the process, and checks if it is running. Maintains the
  screen recording process as a subprocess.Popen object. This class is not
  thread-safe. This class is intended to be used by the ScreenRecorder class.
  """

  def __init__(self, serial: str, screen_recording_path: str):
    """Initializes the ScreenRecordingProcess.

    Args:
      serial: The serial number of the device.
      screen_recording_path: The path to the screen recording directory on the
        device.
    """
    self._serial = serial
    self._path = screen_recording_path
    self._process = None

  def is_running(self) -> bool:
    """Checks if the screen recording process is running.

    Returns:
      True if the screen recording process is running, False otherwise.
    """
    return self._process is not None and self._process.poll() is None

  def stop(self) -> None:
    """Stops the screen recording process.

    Noop if the process is not running.
    """
    self._stop()

  def start(self) -> None:
    """Makes sure the screen recording process is running.

    Starts the process if it is not running, or if it was terminated. Noop if
    the process is already running.
    """
    if self._process is None:
      self._process = self._start()
    else:
      return_code = self._process.poll()
      if return_code is not None:
        _log_debug(
            'Screen recording process terminated with return code %d,'
            ' restarting...',
            return_code,
        )
        self._process = self._start()

  def _start(self) -> subprocess.Popen[str]:
    """Starts the screen recording process.

    Returns:
      The subprocess.Popen object of the screen recording process.
    """
    _log_debug('Starting screen recording process...')
    return subprocess.Popen(
        [
            'adb',
            '-s',
            self._serial,
            'shell',
            'screenrecord',
            os.path.join(
                self._path,
                f'{time.strftime('%Y-%m-%d_%H:%M:%S', time.gmtime())}.mp4',
            ),
            '--time-limit',
            '0',
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

  def _stop(self, timeout_seconds: int = 10) -> None:
    """Stops the screen recording process.

    Args:
      timeout_seconds: The timeout in seconds to wait for the process to stop.
        If the process does not stop after the timeout, it will be killed.
    """
    if not self._process:
      _log_debug('Screen recording process is not running.')
      return
    _log_debug('Terminating screen recording process...')
    self._process.terminate()
    try:
      self._process.wait(timeout_seconds)
    except subprocess.TimeoutExpired:
      _log_warning(
          'Screen recording process did not stop after %d seconds.',
          timeout_seconds,
      )
      # kill the process if it did not stop after the timeout
      self._process.kill()

  def _kill(self) -> None:
    """Kills the screen recording process."""
    if self._process:
      self._process.kill()


class ScreenRecorder:
  """Manages a thread to start/restart the process in the background."""

  # The path to the screen recording directory on the device. This path is
  # created on the device before starting the screen recording process.
  # Preferred over /data/local/tmp because /data/local/tmp may be cleaned up
  # after a reboot.
  _DEVICE_PATH = '/sdcard/screen_recording/'
  _WATCHER_THREAD_NAME = 'screen_recording_watcher_thread'
  _WATCHER_THREAD_LOOP_INTERVAL_SECONDS = 1
  # The timeout in seconds to wait for the device to be ready before
  # restarting the screen recording process, or copying the screen recording
  # files to the output path.
  _DEVICE_READY_TIMEOUT_SECONDS = 10

  _controller: android_device.AndroidDevice
  _watcher_thread: threading.Thread | None = None
  _cancel_event: threading.Event

  def __init__(self, controller: android_device.AndroidDevice):
    """Initializes the ScreenRecorder.

    Args:
      controller: An AndroidDevice object used to interact with the device.
    """
    self._controller = controller
    self._watcher_thread = None
    self._cancel_event = threading.Event()
    atexit.register(self._cleanup)

  def start(self) -> None:
    """Starts the screen recording process.

    Noop if the screen recording process is already started.
    """
    # if watcher thread exists, then the process is assumed to be started
    # because the thread keeps restarting the process if it is terminated.
    if self._watcher_thread:
      _log_warning('Screen recording is already started.')
      return

    # create the watcher thread to maintain the screen recording process
    _log_info('Starting screen recording...')
    self._controller.adb.shell(['mkdir', '-p', self._DEVICE_PATH])
    self._cancel_event.clear()
    # watcher thread will start the screen recording process and restart it if
    # it is terminated.
    self._watcher_thread = threading.Thread(
        target=self._watch,
        args=(self._DEVICE_PATH,),
        # make sure the thread is not blocking the main/test process termination
        daemon=True,
        name=self._WATCHER_THREAD_NAME,
    )
    self._watcher_thread.start()

  def stop(self, output_path: str) -> None:
    """Stops the screen recording process and copies the files to the output path.

    Args:
      output_path: The path to the output directory.
    """
    _log_info('Stopping screen recording...')
    self._cancel_and_join_watcher_thread()
    try:
      self._copy_screen_recording_files(output_path)
    except android_device.adb.AdbError as e:
      # ignore the error if the file is not found, or if permission is denied
      _log_warning('Failed to copy screen recording files: %s', e)

  def _cleanup(self) -> None:
    """Cleans up the screen recording process.

    Won't copy the screen recording files to the output path, nor will it delete
    the screen recording files from the device.
    """
    _log_info('Cleaning up...')
    self._cancel_and_join_watcher_thread()

  def _cancel_and_join_watcher_thread(self) -> None:
    """Cancels the screen recording watcher thread and joins it."""
    self._cancel_event.set()
    if self._watcher_thread:
      _log_debug('Joining screen recording watcher thread...')
      self._watcher_thread.join()
      _log_debug('Screen recording watcher thread joined.')
      self._watcher_thread = None

  def _watch(self, path: str) -> None:
    """Starts the screen recording and monitors the process.

    Starts the screen recording process and restarts it if it is terminated,
    until the cancel signal is received. This method is intended to be run in a
    separate thread.

    Args:
      path: The path to the screen recording directory.
    """
    screen_recording_process = ScreenRecordingProcess(
        self._controller.serial, path
    )
    try:
      # check if the cancel event is set - if it is set, exit the loop and stop
      # the process.
      while not self._cancel_event.is_set():
        if not screen_recording_process.is_running():
          # check if the device is ready before restarting the process
          if self._is_device_ready():
            screen_recording_process.start()
          else:
            _log_debug('Device is not ready.')
        time.sleep(self._WATCHER_THREAD_LOOP_INTERVAL_SECONDS)
      _log_debug('Screen recording watcher is cancelled.')
    except Exception as e:  # pylint: disable=broad-except
      _log_warning('Screen recording watcher thread is interrupted: %s', e)
    finally:
      screen_recording_process.stop()

  def _is_device_ready(self) -> bool:
    """Checks if the device is ready.

    This method blocks the thread until the device is ready, or the timeout (10
    seconds) is reached. It is used to check if the device is ready before
    restarting the screen recording process.

    Returns:
      True if the device is ready, False otherwise.
    """
    try:
      self._controller.adb.wait_for_device(
          timeout=self._DEVICE_READY_TIMEOUT_SECONDS
      )
    except android_device.adb.AdbTimeoutError:
      return False
    return True

  def _copy_screen_recording_files(self, output_path: str) -> None:
    """Copies the screen recording files from the device to the output path.

    Args:
      output_path: The path to the output directory.
    """
    _log_debug('Copying screen recording files to %s', output_path)
    if not self._is_device_ready():
      _log_warning('Device is not ready, skipping screen recording copy.')
      return
    # to avoid permission denied errors when copying the file
    self._controller.root_adb()
    files = (
        self._controller.adb.shell(['ls', self._DEVICE_PATH])
        .decode('utf-8')
        .splitlines()
    )
    _log_debug('Screen recording files: %s', files)
    for file in files:
      file_path = os.path.join(self._DEVICE_PATH, file)
      self._controller.adb.pull([file_path, output_path])
      # remove the file from the device after copying it to the host
      self._controller.adb.shell(['rm', '-f', file_path])
