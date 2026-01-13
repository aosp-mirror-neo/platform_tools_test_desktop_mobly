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

"""A test that exercises PASIT Device component tests."""

import logging
from unittest import mock

from lib.pasit import display_painter
from lib.pasit import pasit_device
from lib.pasit import pasit_test
from lib.pasit import pasit_test_config
from lib.utils import image
from mobly import asserts
from mobly import test_runner


class PasitTestTest(pasit_test.PasitTestClass):

  disable_screen_recording = True

  def setup_class(self):
    super().setup_class()
    self.real_reset = self.dut.reset

  def setup_test(self):
    super().setup_test()
    # allow tracking of the number of calls to the reset method
    self.dut.reset = mock.MagicMock(wraps=self.real_reset)

  def test_unexpected_reboot(self):
    logging.info('Rebooting device...')
    # access protect method to bypass all the setup post reboot and ensure this
    # is detected as unexpected reboot
    self.dut._servo.cold_reset()
    logging.info('Waiting for device to boot...')
    self.dut.wait_for_device_online()
    logging.info('Checking if reboot was detected rebooted...')
    asserts.assert_true(
        self.dut.unexpected_reboots(), 'Unexpected reboot not detected.'
    )
    # ensure test doesn't fail on teardown by handling the unexpected reboot in
    # the test.
    try:
      self.dut.recover_unexpected_reboot()
    except pasit_device.PasitDeviceError as e:
      asserts.abort_class(
          'Failed to recover from unexpected reboot, DUT may be in an'
          f' unrecoverable state: {e}'
      )

  def test_unexpected_reboot_part2(self):
    # this test checks that the dut is recovered properly after a reboot, it
    # relies on the test above to reboot the dut and run first and is not
    # intended to be run alone.

    # show color to validate that UI controls and app launching works, this will
    # also validate that the DUT is not logged out or at the lock screen.
    self.painter = self.create(display_painter)
    self.painter.show_color_on_display(image.NamedColor.GREEN.value)
    self.painter.clean_color_on_display()

  def test_reboot_behavior_on_teardown_on_success(self):
    self.reboot_policy = pasit_test_config.RebootPolicy.ON_TEARDOWN_TEST
    # Test succeeds, reboot expected
    asserts.assert_true(True, 'This should not fail')

  def teardown_test(self):
    super().teardown_test()
    if (
        self.current_test_info.name
        == 'test_reboot_behavior_on_teardown_on_success'
    ):
      # Validate that the dut was rebooted on teardown.
      self.dut.reset.assert_called_once()
      self.reboot_policy = pasit_test_config.RebootPolicy.NONE


if __name__ == '__main__':
  test_runner.main()
