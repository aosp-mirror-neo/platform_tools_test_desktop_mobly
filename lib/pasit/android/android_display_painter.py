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

import logging
import os
import sys

from lib.pasit import pasit_display
from lib.pasit.android import android_ui_tools
from lib.pasit.android import dumpsys_display_parser
from lib.pasit.base import base_display_painter
from lib.utils import image
from lib.utils import retry
from mobly.controllers import android_device
from mobly.controllers.android_device_lib import adb
from mobly.controllers.android_device_lib import apk_utils

DisplayPainterError = base_display_painter.BaseDisplayPainter.Error

START_COLOR_FILL_TEST_APP_RETRY_POLICY = retry.RetryPolicy(
    max_tries=10, delay_seconds=1
)
STOP_COLOR_FILL_TEST_APP_RETRY_POLICY = retry.RetryPolicy(
    max_tries=3, delay_seconds=1
)
DETECT_EXPECTED_WINDOW_COUNT_RETRY_POLICY = retry.RetryPolicy(
    max_tries=3, delay_seconds=5
)


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

  _COLOR_FILL_TEST_APP_APK_PATH = os.path.join(
      os.path.dirname(os.path.abspath(sys.argv[0])),
      'ColorFillTest.apk',
  )
  _COLOR_FILL_TEST_APP: android_ui_tools.AndroidUIApplication = (
      android_ui_tools.AndroidUIApplication.COLOR_FILL_TEST_APP
  )

  def __init__(self, controller: android_device.AndroidDevice):
    """Initializes the AndroidDisplayPainter.

    Installs the ColorFillTestApp on the Android device.

    Args:
      controller: The Android device controller.
    """
    super().__init__(controller)
    self.ui_tools = android_ui_tools.AndroidUITools(self.controller)
    self.package_name = self.ui_tools.get_app_package_name(
        self._COLOR_FILL_TEST_APP
    )
    # uninstall the app to avoid INSTALL_FAILED_UPDATE_INCOMPATIBLE error
    apk_utils.uninstall(self.controller, self.package_name)

  def cleanup(self):
    """Cleans up after testing.

    Uninstalls the ColorFillTestApp when the object is garbage collected.
    """
    self.ui_tools.stop_app(self._COLOR_FILL_TEST_APP)
    if self.ui_tools.is_app_installed(self._COLOR_FILL_TEST_APP):
      apk_utils.uninstall(self.controller, self.package_name)

  def show_color_on_display(
      self,
      color: image.Color,
      display_id: pasit_display.PasitDisplay.DisplayId | None = None,
  ):
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
    if not self.ui_tools.is_app_installed(self._COLOR_FILL_TEST_APP):
      apk_utils.install(
          self.controller,
          self._COLOR_FILL_TEST_APP_APK_PATH,
          params=['-t'],  # to allow installing test packages
      )
    self._set_screen_brightness(255)

    window_count_before = self.ui_tools.get_window_count(
        self._COLOR_FILL_TEST_APP
    )
    # starting the app may fail, retry a few times to ensure color is shown
    retry.retry(
        lambda: self._try_show_color_on_display(
            color, window_count_before + 1, display_id
        ),
        exceptions=(DisplayPainterError,),
        policy=START_COLOR_FILL_TEST_APP_RETRY_POLICY,
    )
    # maximize the window that shows custom background color
    self.ui_tools.maximize_app_window(self._COLOR_FILL_TEST_APP)

  def clean_color_on_display(self):
    """Cleans up the color on the display.

    This function closes all instances of the ColorFillTestApp. If the app was
    started on multiple displays (by calling `show_color_on_display` with
    different `display_id`s), all those instances will be stopped.
    """
    retry.retry(
        self._try_clean_color_on_display,
        exceptions=(DisplayPainterError,),
        policy=STOP_COLOR_FILL_TEST_APP_RETRY_POLICY,
    )

  def _try_show_color_on_display(
      self,
      color: image.Color,
      expected_window_count: int,
      display_id: pasit_display.PasitDisplay.DisplayId | None,
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
        lambda: self.ui_tools.get_window_count(self._COLOR_FILL_TEST_APP),
        until=lambda window_count: window_count >= expected_window_count,
        policy=DETECT_EXPECTED_WINDOW_COUNT_RETRY_POLICY,
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
    self.ui_tools.stop_app(self._COLOR_FILL_TEST_APP)

    # wait.gone is used to prevent StaleObjectException
    # use retry because there may be more than one window
    # return False if the color fill test app is still present
    if not retry.retry(
        lambda: self.ui_tools.wait_app_close(self._COLOR_FILL_TEST_APP),
        until=lambda _: not self.ui_tools.wait_app_open(
            self._COLOR_FILL_TEST_APP
        ),
        # The policy is defined locally because it is implementation specific.
        # Wait to receive `gone` for every window
        # We expect to have no more than 3 windows (with 2 external monitors),
        # number of tries is set to 10 as a precaution.
        policy=retry.RetryPolicy(max_tries=10, delay_seconds=1),
    ):
      raise DisplayPainterError('Color fill test app window still exists.')

    # wait for 0 windows count that show custom background color
    window_count = retry.retry(
        lambda: self.ui_tools.get_window_count(self._COLOR_FILL_TEST_APP),
        until=lambda window_count: window_count == 0,
        policy=DETECT_EXPECTED_WINDOW_COUNT_RETRY_POLICY,
    )
    if window_count != 0:
      raise DisplayPainterError(
          'Color fill test app window count did not decrease to 0. Actual'
          f' window count: {window_count}'
      )

  def _start_color_fill_test_app(
      self,
      color: image.Color,
      display_id: pasit_display.PasitDisplay.DisplayId | None,
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
              f'{self.package_name}/.MainActivity',
              '-a',
              'android.intent.activity.MAIN',
              '-e',
              'color',
              repr(color),
          ]
          + (['--display', display_id] if display_id else [])
      )
    except adb.AdbError as e:
      if 'Permission Denial' in str(e):
        # frequent failure is due to trying to start the app on a disconnected
        # or invalid display_id, so handle this error separately and provide
        # more useful error message.
        connected_display_ids = dumpsys_display_parser.DumpsysDisplayParser(
            self.controller
        ).get_display_ids()
        logging.debug('Currently connected displays: %s', connected_display_ids)
        if display_id not in connected_display_ids:
          raise DisplayPainterError(
              f'Failed to start color fill test app on display ID {display_id},'
              ' display is not connected.'
          ) from e
      raise DisplayPainterError('Failed to start color fill test app') from e

  def _set_screen_brightness(self, brightness: int):
    """Sets the screen brightness. Max brightness is 255."""
    self.controller.adb.shell(
        ['settings', 'put', 'system', 'screen_brightness', str(brightness)]
    )
