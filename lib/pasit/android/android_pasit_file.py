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

"""AndroidPasitFile handles file operations for PASIT testing on Android devices."""

import os

from lib.pasit.base import base_pasit_file
from mobly.controllers.android_device_lib import adb


class AndroidPasitFile(base_pasit_file.BasePasitFile):
  """File interface for Android devices."""

  def push_file(self, file_path: str, dest_path: str):
    self.controller.adb.push([file_path, dest_path])

  def pull_file(self, file_path: str, dest_path: str):
    self.controller.adb.pull([file_path, dest_path])

  def list_files(self, directory_path: str) -> list[str]:
    try:
      files = (
          self.controller.adb.shell(['ls', directory_path])
          .decode('utf-8')
          .splitlines()
      )
      return [os.path.join(directory_path, file) for file in files]
    except adb.AdbError as e:
      if b'No such file or directory' in e.stderr:
        raise FileNotFoundError(
            f'Directory {directory_path} does not exist on the device.'
        ) from e
      else:
        raise

  def copy_file(self, file_path: str, dest_path: str):
    self.controller.adb.shell(['cp', file_path, dest_path])

  def remove_file(self, file_path: str, force: bool = False):
    if force:
      self.controller.adb.shell(['rm', '-f', file_path])
    else:
      self.controller.adb.shell(['rm', file_path])
