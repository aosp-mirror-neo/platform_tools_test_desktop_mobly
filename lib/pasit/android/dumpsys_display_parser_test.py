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

"""Unit tests for dumpsys_display_parser."""

import unittest
from unittest import mock
from lib.pasit.android import android_display_id
from lib.pasit.android import dumpsys_display_parser
from lib.pasit.base import base_pasit_display

DisplayId = android_display_id.AndroidDisplayId
DisplayResolution = base_pasit_display.BasePasitDisplay.DisplayResolution


class DumpsysDisplayParserTest(unittest.TestCase):

  def setUp(self):
    self.internal_display_lines = [
        (
            '    mBaseDisplayInfo=DisplayInfo{"Built-in Screen", displayId 0,'
            ' displayGroupId 0, FLAG_SECURE, FLAG_SUPPORTS_PROTECTED_BUFFERS,'
            ' FLAG_PRESENTATION, FLAG_TRUSTED, FLAG_ALLOWS_CONTENT_MODE_SWITCH,'
            ' real 1920 x 1200, largest app 1920 x 1200, smallest app 1920 x'
            ' 1200, appVsyncOff 1000000, presDeadline 16659474, mode 1,'
            ' renderFrameRate 60.025906, hasArrSupport false,'
            ' frameRateCategoryRate FrameRateCategoryRate {normal=60.0,'
            ' high=90.0}, supportedRefreshRates [60.025906], defaultMode 1,'
            ' userPreferredModeId -1, supportedModes [{id=1, width=1920,'
            ' height=1200, fps=60.025906, vsync=60.025906, synthetic=false,'
            ' alternativeRefreshRates=[], supportedHdrTypes=[]}],'
            ' appsSupportedModes [{id=1, width=1920, height=1200,'
            ' fps=60.025906, vsync=60.025906, synthetic=false,'
            ' alternativeRefreshRates=[], supportedHdrTypes=[]}],'
            ' hdrCapabilities HdrCapabilities{mSupportedHdrTypes=[],'
            ' mMaxLuminance=500.0, mMaxAverageLuminance=500.0,'
            ' mMinLuminance=0.0}, isForceSdr false, userDisabledHdrTypes [],'
            ' minimalPostProcessingSupported false, rotation 0, state ON,'
            ' committedState ON, type INTERNAL, uniqueId'
            ' "local:4613568140281232128", app 1920 x 1200, density 220'
            ' (162.01993 x 162.12766) dpi, layerStack 0, colorMode 0,'
            ' supportedColorModes [0], address {port=0,'
            ' model=0x4006afc7a485bb}, deviceProductInfo'
            ' DeviceProductInfo{name=, manufacturerPnpId=AUO, productId=53905,'
            ' modelYear=null, manufactureDate=ManufactureDate{week=22,'
            ' year=2020}, connectionToSinkType=1}, removeMode 0,'
            ' refreshRateOverride 0.0, brightnessMinimum 0.0, brightnessMaximum'
            ' 1.0, brightnessDefault 0.39763778, brightnessDim 0.05,'
            ' installOrientation ROTATION_0, layoutLimitedRefreshRate null,'
            ' hdrSdrRatio not_available, thermalRefreshRateThrottling {},'
            ' thermalBrightnessThrottlingDataId default, canHostTasks true}'
        ),
        (
            '    mOverrideDisplayInfo=DisplayInfo{"Built-in Screen", displayId'
            ' 0, displayGroupId 0, FLAG_SECURE,'
            ' FLAG_SUPPORTS_PROTECTED_BUFFERS, FLAG_PRESENTATION, FLAG_TRUSTED,'
            ' FLAG_ALLOWS_CONTENT_MODE_SWITCH, real 1920 x 1200, largest app'
            ' 1920 x 1920, smallest app 1200 x 1200, appVsyncOff 1000000,'
            ' presDeadline 16659474, mode 1, renderFrameRate 60.025906,'
            ' hasArrSupport false, frameRateCategoryRate FrameRateCategoryRate'
            ' {normal=60.0, high=90.0}, supportedRefreshRates [60.025906],'
            ' defaultMode 1, userPreferredModeId -1, supportedModes [{id=1,'
            ' width=1920, height=1200, fps=60.025906, vsync=60.025906,'
            ' synthetic=false, alternativeRefreshRates=[],'
            ' supportedHdrTypes=[]}], appsSupportedModes [{id=1, width=1920,'
            ' height=1200, fps=60.025906, vsync=60.025906, synthetic=false,'
            ' alternativeRefreshRates=[], supportedHdrTypes=[]}],'
            ' hdrCapabilities HdrCapabilities{mSupportedHdrTypes=[],'
            ' mMaxLuminance=500.0, mMaxAverageLuminance=500.0,'
            ' mMinLuminance=0.0}, isForceSdr false, userDisabledHdrTypes [],'
            ' minimalPostProcessingSupported false, rotation 0, state ON,'
            ' committedState ON, type INTERNAL, uniqueId'
            ' "local:4613568140281232128", app 1920 x 1200, density 220'
            ' (162.01993 x 162.12766) dpi, layerStack 0, colorMode 0,'
            ' supportedColorModes [0], address {port=0,'
            ' model=0x4006afc7a485bb}, deviceProductInfo'
            ' DeviceProductInfo{name=, manufacturerPnpId=AUO, productId=53905,'
            ' modelYear=null, manufactureDate=ManufactureDate{week=22,'
            ' year=2020}, connectionToSinkType=1}, removeMode 0,'
            ' refreshRateOverride 0.0, brightnessMinimum 0.0, brightnessMaximum'
            ' 1.0, brightnessDefault 0.39763778, brightnessDim 0.05,'
            ' installOrientation ROTATION_0, layoutLimitedRefreshRate null,'
            ' hdrSdrRatio not_available, thermalRefreshRateThrottling {},'
            ' thermalBrightnessThrottlingDataId default, canHostTasks true}'
        ),
    ]

  def test_get_display_ids(self):
    self.parser = self._get_parser(self.internal_display_lines)
    self.assertEqual(
        self.parser.get_display_ids(),
        [
            DisplayId(display_id='0', unique_id='4613568140281232128'),
        ],
    )

  def test_get_display_resolution(self):
    self.parser = self._get_parser(self.internal_display_lines)
    self.assertEqual(
        self.parser.get_display_resolution(),
        DisplayResolution(width=1920, height=1200),
    )

  def test_get_supported_display_resolutions(self):
    self.parser = self._get_parser(self.internal_display_lines)
    self.assertEqual(
        self.parser.get_supported_display_resolutions(),
        {
            '1': DisplayResolution(width=1920, height=1200),
        },
    )

  def _get_parser(self, display_lines):
    controller = mock.MagicMock()
    controller.adb.shell.return_value = '\n'.join(display_lines).encode('utf-8')
    return dumpsys_display_parser.DumpsysDisplayParser(controller)


if __name__ == '__main__':
  unittest.main()
