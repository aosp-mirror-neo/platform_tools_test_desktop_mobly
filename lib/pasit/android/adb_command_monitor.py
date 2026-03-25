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

"""Manages a monitored ADB command process for Android devices."""

import os
import pathlib
from typing import Callable

from lib.utils import process_monitor
from lib.utils import retry
from mobly.controllers import android_device


class AdbCommandMonitor(process_monitor.ProcessMonitor):
  """Manages and monitors an ADB command as a background process on a device.

  This class extends ProcessMonitor to tailor it for commands run via ADB
  on an Android device. It handles device readiness checks before
  starting/restarting the command and can pull generated files from the device
  to the host upon stopping.

  Attributes:
    controller: The Mobly AndroidDevice controller instance.
    log: The logger adapter instance for prefixed logging.
  """

  # The timeout in seconds to wait for the device to be ready before
  # restarting the process.
  _DEVICE_READY_TIMEOUT_SECONDS = 10
  _BOOT_COMPLETION_TIMEOUT_SECONDS = 10

  controller: android_device.AndroidDevice
  _output_path: str

  def __init__(
      self,
      command: Callable[[], list[str]],
      process_name: str,
      controller: android_device.AndroidDevice,
      output_path: str,
  ):
    """Initializes the AdbCommandMonitor.

    Note that the `command` will be executed in a separate thread.

    Args:
      command: A callable that returns the ADB command to run.
      process_name: The name of the process, used for logging.
      controller: An AndroidDevice object used to interact with the device.
      output_path: The absolute path on the device where the command will
        generate output files.
    """
    super().__init__(
        name=process_name,
        command=command,
        start_condition=self._is_device_ready,
    )
    self.controller = controller
    self._output_path = output_path

  def start(self) -> None:
    """Creates the output directory on the device and starts the monitor.

    Ensures the device-side output directory exists before delegating
    to the superclass's start method to launch the watcher thread.
    """
    self._wait_for_output_directory()
    self.controller.adb.shell(['mkdir', '-p', self._output_path])

    super().start()  # pylint: disable=attribute-error

  def stop(self, host_output_path: str | None = None) -> None:
    """Stops the monitor and optionally pulls files from the device.

    Args:
      host_output_path: The path on the host machine to copy the files to. If
        None, file copying is skipped.
    """
    super().stop()  # pylint: disable=attribute-error

    if not host_output_path:
      return

    if not self._is_device_ready():
      self.log.warning('Device is not ready, skipping captured files copy.')
      return

    captured_files = (
        self.controller.adb.shell(['ls', self._output_path])
        .decode('utf-8')
        .splitlines()
    )

    if not captured_files:
      self.log.debug('No captured files found on the device.')
      return

    try:
      self._copy_captured_files(captured_files, host_output_path)
    except android_device.adb.AdbError as e:
      # ignore the error if the file is not found, or if permission is denied
      self.log.warning('Failed to copy captured files: %s', e)

  def _is_device_ready(self) -> bool:
    """Checks if the Android device is ready for interaction.

    Verifies that the device is connected via ADB and has completed booting.
    This method can block up to the defined timeouts.

    Note: this methods is executed in the ProcessMonitor watcher thread.

    Returns:
      True if the device is ready, False otherwise.
    """
    try:
      self.controller.adb.wait_for_device(
          timeout=self._DEVICE_READY_TIMEOUT_SECONDS
      )
      self.controller.wait_for_boot_completion(
          timeout=self._BOOT_COMPLETION_TIMEOUT_SECONDS
      )
    except android_device.adb.AdbTimeoutError:
      return False
    return True

  def _wait_for_output_directory(self) -> None:
    """Waits for the storage mount on the device to be available.

    Retries the ADB command to check if the output directory parent exists up to
    5 times with a 5 second delay between each attempt.

    Note: this method is executed in the ProcessMonitor watcher thread.

    Raises:
      adb.AdbError: If the output directory parent does not exist after 5
        attempts.
    """
    parent_path = pathlib.PurePosixPath(self._output_path).parent
    retry.retry(
        # 'test -d <path>' command exits with 0 if the path exists and is a
        # directory, and non-zero otherwise. adb.shell raises an AdbError for
        # non-zero exit codes.
        lambda: self.controller.adb.shell([
            'test',
            '-d',
            str(parent_path),
        ]),
        exceptions=(android_device.adb.AdbError,),
        policy=retry.RetryPolicy(
            max_tries=5,
            delay_seconds=5,
        ),
    )

  def _copy_captured_files(
      self, captured_files: list[str], host_output_path: str
  ) -> None:
    """Copies specified files from the device to the host.

    Roots ADB to ensure permissions, then pulls each file and removes
    it from the device after successful copy.

    Args:
      captured_files: A list of file names (not full paths) within the
        device_output_path.
      host_output_path: The destination directory on the host.

    Raises:
      adb.AdbError: If any ADB command fails.
    """
    self.log.info('Copying captured files to %s', host_output_path)
    # to avoid permission denied errors when copying the file
    self.controller.root_adb()
    self.log.debug('Captured files: %s', captured_files)
    for file in captured_files:
      file_path = os.path.join(self._output_path, file)
      self.controller.adb.pull([file_path, host_output_path])
      # remove the file from the device after copying it to the host
      self.controller.adb.shell(['rm', '-f', file_path])
