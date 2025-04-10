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

"""AndroidPasitCamera handles camera operations for PASIT testing on Android devices."""

from collections.abc import MutableSequence

from mobly.controllers import android_device

from pasit.lib.base import base_pasit_camera


class AndroidPasitCamera(base_pasit_camera.BasePasitCamera):
  """PasitCamera for Android devices."""

  def launch_camera_app(self):
    # Instruct the Activity Manager(am) to start the camera app using the
    # VIDEO_CAPTURE action. This is a typical way to launch the camera app on
    # Android devices.
    self.controller.adb.shell([
        'am',
        'start',
        '-a',
        'android.media.action.VIDEO_CAPTURE',
        'com.google.android.desktop.camera',
    ])

  def close_camera_app(self):
    # Instruct the Activity Manager(am) to terminate all processes associated
    # with the camera app (uniquely identified by package name
    # com.google.android.desktop.camera).
    self.controller.adb.shell(
        ['am', 'force-stop', 'com.google.android.desktop.camera']
    )

  def get_connected_cameras(self) -> MutableSequence[str]:
    return [
        item
        for item in self.controller.adb.shell(['ls', '/dev/video*'])
        .decode('utf-8')
        .split('\n')
        if item
    ]

  def is_camera_app_using_camera(self, camera_device: str) -> bool:
    try:
      # use lsof to check if the camera device is being used, this assumes that
      # the camera devices is being used by the camera app and not by any other
      # process. Checking that the cameraserv process is using the camera device
      # is not possible as it doesn't work for all internal cameras.
      output = self.controller.adb.shell(['lsof', camera_device]).decode(
          'utf-8'
      )
    except android_device.adb.AdbError:
      # The command fails when grep returns empty. Catch the error and return
      # False.
      return False
    return bool(output)
