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

"""AndroidDisplayPainter shows colors on Android device displays for testing."""

import os
import sys

from lib.pasit.base import base_display_painter
from lib.utils import image
from lib.utils import retry
from mobly import signals
from mobly.controllers import android_device
from mobly.controllers.android_device_lib import apk_utils


class AndroidDisplayPainter(base_display_painter.BaseDisplayPainter):
  """AndroidDisplayPainter shows colors on Android device displays for testing.

  This class uses the ColorFillTestApp to show colors on the screen. The
  ColorFillTestApp is a simple Android app that fills the screen with a
  specified color. It is installed ad-hoc, and uninstalled when the object is
  garbage collected.

  The class also uses UI Automator to verify that the ColorFillTestApp window
  has been
  created, to maximize the window, and to clean up after testing. UI Automator
  is expected to be registered in the controller. PasitDevice already does that
  in its __init__.
  """

  COLOR_FILL_TEST_APP_PACKAGE_NAME = 'com.google.android.colorfilltestapp'
  COLOR_FILL_TEST_APP_APK_PATH = os.path.join(
      os.path.dirname(os.path.abspath(sys.argv[0])),
      'ColorFillTest.apk',
  )
  COLOR_FILL_TEST_APP_ACTIVITY_NAME = (
      f'{COLOR_FILL_TEST_APP_PACKAGE_NAME}/.MainActivity'
  )
  COLOR_FILL_TEST_APP_WINDOW_DESCRIPTION = 'Color Fill Test'

  def __init__(self, controller: android_device.AndroidDevice):
    """Initializes the AndroidDisplayPainter.

    Installs the ColorFillTestApp on the Android device.

    Args:
      controller: The Android device controller.
    """
    super().__init__(controller)
    apk_utils.install(
        self.controller,
        self.COLOR_FILL_TEST_APP_APK_PATH,
        params=['-t'],  # to allow installing test packages
    )

  def __del__(self):
    """Cleans up after testing.

    Uninstalls the ColorFillTestApp when the object is garbage collected.
    """
    apk_utils.uninstall(self.controller, self.COLOR_FILL_TEST_APP_PACKAGE_NAME)

  def show_color_on_display(self, color: image.Color, display_id: str = ''):
    # set screen brightness to max to ensure color is visible
    self._set_screen_brightness(255)

    window_count_before = self._get_color_fill_test_app_window_count()
    self.controller.adb.shell(
        [
            'am',
            'start',
            '-n',
            self.COLOR_FILL_TEST_APP_ACTIVITY_NAME,
            '-a',
            'android.intent.activity.MAIN',
            '-e',
            'color',
            repr(color),
        ]
        + (['--display', display_id] if display_id else [])
    )

    window_count_after = retry.retry(
        lambda: self._get_color_fill_test_app_window_count(),
        until=lambda window_count: window_count == window_count_before + 1,
        max_tries=10,
        delay_seconds=1,
    )
    if window_count_after <= window_count_before:
      raise signals.TestError(
          'Failed to show color on display. Color fill test app window count'
          f' did not increase by 1. Before: {window_count_before}, After:'
          f' {window_count_after}'
      )
    # maximize the window that shows custom background color
    self._maximize_color_fill_test_app_window()

  def clean_color_on_display(self):
    window_count_before = self._get_color_fill_test_app_window_count()
    self.controller.adb.shell([
        'am',
        'force-stop',
        self.COLOR_FILL_TEST_APP_PACKAGE_NAME,
    ])
    window_count_after = retry.retry(
        lambda: self._get_color_fill_test_app_window_count(),
        until=lambda window_count: window_count == 0,
        max_tries=10,
        delay_seconds=1,
    )
    if window_count_after != 0:
      raise signals.TestError(
          'Failed to clean color on display. Color fill test app window count'
          f' did not become 0. Before: {window_count_before}, After:'
          f' {window_count_after}'
      )

  def _set_screen_brightness(self, brightness: int):
    """Sets the screen brightness. Max brightness is 255."""
    self.controller.adb.shell(
        ['settings', 'put', 'system', 'screen_brightness', str(brightness)]
    )

  def _get_color_fill_test_app_window_count(self) -> int:
    """Returns the number of windows that show custom background color."""
    return self.controller.ui(
        desc=(
            f'{self.COLOR_FILL_TEST_APP_WINDOW_DESCRIPTION} (Desktop windowing)'
        )
    ).count

  def _maximize_color_fill_test_app_window(self):
    """Maximizes the window that shows custom background color."""
    self.controller.ui(
        desc=f'Maximize {self.COLOR_FILL_TEST_APP_WINDOW_DESCRIPTION}'
    ).click()
