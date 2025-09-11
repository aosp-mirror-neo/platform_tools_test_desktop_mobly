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

import datetime
import os
import sys

from lib.pasit.base import base_display_painter
from lib.utils import image
from lib.utils import retry
from mobly.controllers import android_device
from mobly.controllers.android_device_lib import adb
from mobly.controllers.android_device_lib import apk_utils

DisplayPainterError = base_display_painter.BaseDisplayPainter.Error


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
    # uninstall the app to avoid INSTALL_FAILED_UPDATE_INCOMPATIBLE error
    apk_utils.uninstall(self.controller, self.COLOR_FILL_TEST_APP_PACKAGE_NAME)
    apk_utils.install(
        self.controller,
        self.COLOR_FILL_TEST_APP_APK_PATH,
        params=['-t'],  # to allow installing test packages
    )

  def cleanup(self):
    """Cleans up after testing.

    Uninstalls the ColorFillTestApp when the object is garbage collected.
    """
    self._force_stop_color_fill_test_app()
    apk_utils.uninstall(self.controller, self.COLOR_FILL_TEST_APP_PACKAGE_NAME)

  def show_color_on_display(self, color: image.Color, display_id: str = ''):
    """Shows the specified color on the Android device display.

    This method launches the ColorFillTestApp to display a solid color.
    It sets the screen brightness to maximum to ensure visibility and
    retries the app launch multiple times if it fails initially.
    The app can be launched on a specific display by providing `display_id`.
    Importantly, this method supports multiple displays; if called for
    different `display_id`s, each specified display will get the color APK
    on that display.

    Args:
      color: The color to display on the screen.
      display_id: The ID of the display to show the color on. If empty, the
        color will be shown on the default display.
    """
    # set screen brightness to max to ensure color is visible
    self._set_screen_brightness(255)

    window_count_before = self._get_color_fill_test_app_window_count()
    # starting the app may fail, retry a few times to ensure color is shown
    retry.retry(
        lambda: self._try_show_color_on_display(
            color, window_count_before + 1, display_id
        ),
        exceptions=(DisplayPainterError,),
        max_tries=10,
        delay_seconds=1,
    )
    # maximize the window that shows custom background color
    self._maximize_color_fill_test_app_window()

  def clean_color_on_display(self):
    """Cleans up the color on the display.

    This function closes all instances of the ColorFillTestApp. If the app was
    started on multiple displays (by calling `show_color_on_display` with
    different `display_id`s), all those instances will be stopped.
    """
    retry.retry(
        self._try_clean_color_on_display,
        exceptions=(DisplayPainterError,),
    )

  def _try_show_color_on_display(
      self, color: image.Color, expected_window_count: int, display_id: str
  ):
    """Attempts to start the ColorFillTestApp.

    Args:
      color: The color to show on the display.
      expected_window_count: The expected number of color fill test app windows.
      display_id: The display ID to show the color on.

    Raises:
        DisplayPainterError: If the color fill test app window count did not
        increase to the
        expected number.
    """
    self._start_color_fill_test_app(color, display_id)
    # After starting the app the window may not appear immediately. So we need
    # to retry getting windowcount a few times.
    window_count = retry.retry(
        lambda: self._get_color_fill_test_app_window_count(),
        until=lambda window_count: window_count >= expected_window_count,
        delay_seconds=5,
    )
    if window_count < expected_window_count:
      raise DisplayPainterError(
          'Color fill test app window count did not increase to'
          f' {expected_window_count}. Actual window count: {window_count}'
      )

  def _try_clean_color_on_display(self):
    """Attempts to clean the color on the display.

    Stops the ColorFillTestApp and waits for its window to disappear.

    Raises:
      DisplayPainterError: If the color fill test app window count did not
      decrease to 0.
    """
    self._force_stop_color_fill_test_app()

    # wait.gone is used to prevent StaleObjectException
    # use retry because there may be more than one window
    # return False if the color fill test app is still present
    if not retry.retry(
        lambda: self.controller.ui(
            pkg=self.COLOR_FILL_TEST_APP_PACKAGE_NAME
        ).wait.gone(timeout=datetime.timedelta(seconds=10)),
        until=lambda _: not self.controller.ui(
            pkg=self.COLOR_FILL_TEST_APP_PACKAGE_NAME
        ).exists,
        max_tries=3,
    ):
      raise DisplayPainterError('Color fill test app window still exists.')

    # wait for 0 windows count that show custom background color
    window_count = retry.retry(
        self._get_color_fill_test_app_window_count,
        until=lambda window_count: window_count == 0,
    )
    if window_count != 0:
      raise DisplayPainterError(
          'Color fill test app window count did not decrease to 0. Actual'
          f' window count: {window_count}'
      )

  def _start_color_fill_test_app(
      self, color: image.Color, display_id: str = ''
  ):
    """Starts the ColorFillTestApp with the specified color and display.

    Opens a new window filled with the specified color on the specified display.
    """
    try:
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
    except adb.AdbError as e:
      raise DisplayPainterError(
          'Failed to start color fill test app'
      ) from e

  def _force_stop_color_fill_test_app(self):
    """Forces stop the ColorFillTestApp."""
    self.controller.adb.shell([
        'am',
        'force-stop',
        self.COLOR_FILL_TEST_APP_PACKAGE_NAME,
    ])

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
