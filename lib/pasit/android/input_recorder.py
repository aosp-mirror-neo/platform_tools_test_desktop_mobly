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

"""Input recorder for Android devices."""

import os
import time
from lib.pasit.android import adb_command_monitor
from mobly.controllers import android_device


# The path to the input recording directory on the device. This path is
# created on the device before starting the input recording process.
# Preferred over /data/local/tmp because /data/local/tmp may be cleaned up
# after a reboot.
_DEVICE_PATH = '/sdcard/input_recording/'


class InputRecorder(adb_command_monitor.AdbCommandMonitor):
  """Manages an input recording process for Android devices."""

  def __init__(self, controller: android_device.AndroidDevice):
    """Initializes the InputRecorder.

    Args:
      controller: An AndroidDevice object used to interact with the device.
    """
    super().__init__(
        command=lambda: [
            'adb',
            '-s',
            f'{controller.serial}',
            'shell',
            'getevent',
            '-tl',
            '>',
            os.path.join(
                f'{_DEVICE_PATH}',
                f'getevent_{time.strftime("%Y-%m-%d_%H:%M:%S", time.gmtime())}.txt',
            ),
        ],
        process_name='InputRecorder',
        controller=controller,
        output_path=_DEVICE_PATH,
    )
