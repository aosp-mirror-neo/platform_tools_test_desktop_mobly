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
"""Tests for PASIT camera component."""

import logging

from lib.pasit import dut_state_manager
from lib.pasit import pasit_camera
from lib.pasit import pasit_device
from lib.pasit import pasit_test
from lib.utils import functools
from mobly import asserts


@functools.generate_tests
class PasitCameraTest(pasit_test.PasitTestClass):
  """Test for PASIT camera component."""

  def setup_class(self):
    super().setup_class()
    self.camera = self.create(pasit_camera)

  def teardown_test(self):
    self.camera.close_camera_app()
    super().teardown_test()

  def test_camera_app_persists_after_suspend(self):
    """Test camera app persists after suspend and wakeup."""
    logging.info('Launching camera app...')
    asserts.assert_true(
        self.camera.launch_camera_app(), 'Failed to launch camera app.'
    )

    asserts.assert_true(
        self.dut.ui_tools.wait_app_open(pasit_device.UIApplication.CAMERA),
        'Camera app did not open after suspend and wakeup.',
    )
    logging.info('Camera app is open before suspend.')

    dut_state_manager.execute_power_action(
        self.dut, dut_state_manager.PowerAction.SUSPEND
    )

    asserts.assert_true(
        self.dut.ui_tools.wait_app_open(pasit_device.UIApplication.CAMERA),
        'Camera app did not open after suspend and wakeup.',
    )
    logging.info('Camera app is open after suspend and wakeup.')

  def test_launch_camera_app_before_and_after_reboot(self):
    """Test launching the camera app."""
    logging.info('Launching camera app...')
    asserts.assert_true(
        self.camera.launch_camera_app(),
        'Failed to launch camera app before reboot.',
    )

    asserts.assert_true(
        self.dut.ui_tools.wait_app_open(pasit_device.UIApplication.CAMERA),
        'Camera app did not open.',
    )
    logging.info('Camera app is open before reboot.')

    dut_state_manager.execute_power_action(
        self.dut, dut_state_manager.PowerAction.REBOOT
    )
    asserts.assert_false(
        self.dut.ui_tools.wait_app_open(pasit_device.UIApplication.CAMERA),
        'Camera app is still open after reboot.',
    )
    logging.info('Camera app is closed after reboot.')
    logging.info('Launching camera app after reboot...')
    asserts.assert_true(
        self.camera.launch_camera_app(),
        'Failed to launch camera app after reboot.',
    )
    asserts.assert_true(
        self.dut.ui_tools.wait_app_open(pasit_device.UIApplication.CAMERA),
        'Camera app did not open after reboot.',
    )
    logging.info('Camera app is open after reboot.')
