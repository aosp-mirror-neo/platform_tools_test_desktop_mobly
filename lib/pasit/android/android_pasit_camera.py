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
import datetime

from lib.pasit.base import base_pasit_camera
from lib.utils import retry
from mobly.controllers import android_device

CameraError = base_pasit_camera.BasePasitCamera.Error
Mode = base_pasit_camera.BasePasitCamera.Mode


class AndroidPasitCamera(base_pasit_camera.BasePasitCamera):
  """PasitCamera for Android devices."""

  _CAMERA_APP_PACKAGE_NAME = 'com.google.android.desktop.camera'

  _CAMERA_APP_START_RECORDING_BUTTON_DESCRIPTION = 'Start recording'
  _CAMERA_APP_STOP_RECORDING_BUTTON_DESCRIPTION = 'Stop recording'
  _CAMERA_APP_TAKE_PHOTO_BUTTON_DESCRIPTION = 'Take photo'

  _CAMERA_APP_PHOTO_MODE_BUTTON_DESCRIPTION = 'Photo Mode'
  _CAMERA_APP_VIDEO_MODE_BUTTON_DESCRIPTION = 'Video Mode'

  _CAMERA_APP_FILES_PATH = '/data/media/10/DCIM/Camera/'

  _switch_mode_button_description = {
      Mode.VIDEO: _CAMERA_APP_VIDEO_MODE_BUTTON_DESCRIPTION,
      Mode.PHOTO: _CAMERA_APP_PHOTO_MODE_BUTTON_DESCRIPTION,
  }

  _action_button_description = {
      Mode.VIDEO: _CAMERA_APP_START_RECORDING_BUTTON_DESCRIPTION,
      Mode.PHOTO: _CAMERA_APP_TAKE_PHOTO_BUTTON_DESCRIPTION,
  }

  _camera_app_action = {
      Mode.VIDEO: 'android.media.action.VIDEO_CAMERA',
      Mode.PHOTO: 'android.media.action.STILL_IMAGE_CAMERA',
  }

  def launch_camera_app(
      self,
      mode: Mode = Mode.PHOTO,
  ) -> bool:
    self.controller.adb.shell([
        'am',
        'start',
        '-a',
        self._camera_app_action[mode],
        self._CAMERA_APP_PACKAGE_NAME,
    ])
    try:
      return self.controller.ui(pkg=self._CAMERA_APP_PACKAGE_NAME).wait.exists(
          timeout=datetime.timedelta(seconds=20)
      )
    except Exception as e:  # pylint: disable=broad-except
      raise CameraError('Failed to launch camera app') from e

  def close_camera_app(self):
    # Instruct the Activity Manager(am) to terminate all processes associated
    # with the camera app (uniquely identified by package name
    # com.google.android.desktop.camera).
    self.controller.adb.shell(
        ['am', 'force-stop', self._CAMERA_APP_PACKAGE_NAME]
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

  def switch_camera(self):
    try:
      self.controller.ui(
          pkg=self._CAMERA_APP_PACKAGE_NAME, desc='Switch camera'
      ).click()
    except Exception as e:  # pylint: disable=broad-except
      raise CameraError('Failed to switch camera') from e

  def switch_mode(self, mode: Mode) -> bool:
    # Both the photo and video mode buttons are in the same view. Clicking
    # either button toggles to the opposite mode.
    # Retry logic is used to click a button until the desired mode is active.
    retry.retry(
        lambda: self._click_switch_camera_button(mode),
        until=lambda _: self._mode_action_button_exists(mode),
        # The policy is defined locally because it is implementation specific.
        # Retry a few times in case the button was switched to the wrong mode.
        policy=retry.RetryPolicy(max_tries=3, delay_seconds=0),
    )
    return self._mode_action_button_exists(mode)

  def take_photo(self):
    try:
      self.controller.ui(
          pkg=self._CAMERA_APP_PACKAGE_NAME,
          desc=self._CAMERA_APP_TAKE_PHOTO_BUTTON_DESCRIPTION,
      ).click()
    except Exception as e:  # pylint: disable=broad-except
      raise CameraError('Failed to take photo') from e

  def start_recording_video(self):
    try:
      self.controller.ui(
          pkg=self._CAMERA_APP_PACKAGE_NAME,
          desc=self._CAMERA_APP_START_RECORDING_BUTTON_DESCRIPTION,
      ).click()
    except Exception as e:  # pylint: disable=broad-except
      raise CameraError('Failed to start recording video') from e

  def stop_recording_video(self):
    try:
      self.controller.ui(
          pkg=self._CAMERA_APP_PACKAGE_NAME,
          desc=self._CAMERA_APP_STOP_RECORDING_BUTTON_DESCRIPTION,
      ).click()
    except Exception as e:  # pylint: disable=broad-except
      raise CameraError('Failed to stop recording video') from e

  def get_files_path(self) -> str:
    return self._CAMERA_APP_FILES_PATH

  def _mode_action_button_exists(
      self,
      mode: Mode,
      timeout_seconds: int = 5,
  ) -> bool:
    """Finds the capture photo or video action button.

    Args:
      mode: The capture mode to get the action button for.
      timeout_seconds: The timeout in seconds to wait for the action button to
        exist.

    Returns:
      True if the mode action button exists, False otherwise.

    Raises:
      CameraError: If the mode action button cannot be determined.
    """
    try:
      return self.controller.ui(
          pkg=self._CAMERA_APP_PACKAGE_NAME,
          desc=self._action_button_description[mode],
      ).wait.exists(datetime.timedelta(seconds=timeout_seconds))
    except Exception as e:  # pylint: disable=broad-except
      raise CameraError('Failed to check if mode action button exists') from e

  def maximize_camera_app_window(self):
    try:
      self.controller.ui(desc='Maximize Camera').click()
    except Exception as e:  # pylint: disable=broad-except
      raise CameraError('Failed to maximize camera app window') from e

  def _click_switch_camera_button(self, mode: Mode):
    """Clicks the switch camera button.

    Args:
      mode: The capture mode to switch the camera for.

    Raises:
      CameraError: If the switch camera button cannot be clicked.
    """
    try:
      self.controller.ui(
          pkg=self._CAMERA_APP_PACKAGE_NAME,
          desc=self._switch_mode_button_description[mode],
      ).click()
    except Exception as e:  # pylint: disable=broad-except
      raise CameraError('Failed to click switch camera button') from e
