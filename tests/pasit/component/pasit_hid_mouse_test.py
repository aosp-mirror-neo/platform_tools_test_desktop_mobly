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
"""A test that exercises PASIT HID mouse functionality."""

from lib.pasit import hid_emulator
from lib.pasit import pasit_hid
from lib.pasit import pasit_test
from lib.pasit import test_policy
from lib.utils import functools
from lib.utils import retry
from mobly import asserts
from mobly import test_runner


@functools.generate_tests
class PasitHIDMouseTest(pasit_test.PasitTestClass):
  """A test that exercises PASIT HID mouse functionality."""

  hid: pasit_hid.PasitHID
  emulator: hid_emulator.HIDEmulator
  requires_device_type = pasit_test.PasitTestClass.DEVICE_TYPE_HID

  def setup_class(self):
    super().setup_class()
    self.hid = self.create(pasit_hid)
    self.passport_host.activate_device_by_type(self.DEVICE_TYPE_HID)
    self.emulator = hid_emulator.HIDEmulator(self.passport_host)
    retry.retry(
        self.emulator.initialize,
        policy=test_policy.HIDTestPolicy.DETECT_HID_EMULATOR_RETRY_POLICY,
        exceptions=(hid_emulator.HIDEmulator.Error,),
    )
    retry.wait_for_stable_value(
        self.hid.get_hid_emulator_devices,
        timeout_seconds=test_policy.HIDTestPolicy.STABLE_TIMEOUT_SECONDS,
        delay_seconds=test_policy.HIDTestPolicy.STABLE_POLLING_INTERVAL_SECONDS,
        required_stable_duration_seconds=test_policy.HIDTestPolicy.STABLE_REQUIRED_DURATION_SECONDS,
        criteria=lambda devices: len(devices)
        == test_policy.HIDTestPolicy.NUM_HID_DEVICES_EXPECTED,
    )

  def setup_test(self):
    """Handle the setup for the test."""
    super().setup_test()
    self.hid.start_mouse_capture(self.emulator)

  def teardown_test(self):
    """Handle the teardown for the test."""
    self.hid.stop_mouse_capture()
    # avoid passport reset in PasitTestClass.teardown_test
    # super().teardown_test()

  @functools.with_variants(
      left=(hid_emulator.MouseButton.LEFT, pasit_hid.PasitHID.MouseButton.LEFT),
      right=(
          hid_emulator.MouseButton.RIGHT,
          pasit_hid.PasitHID.MouseButton.RIGHT,
      ),
      middle=(
          hid_emulator.MouseButton.MIDDLE,
          pasit_hid.PasitHID.MouseButton.MIDDLE,
      ),
      back=(
          hid_emulator.MouseButton.BACK,
          pasit_hid.PasitHID.MouseButton.BACK,
      ),
      forward=(
          hid_emulator.MouseButton.FORWARD,
          pasit_hid.PasitHID.MouseButton.FORWARD,
      ),
  )
  def test_capture_mouse_click(
      self,
      mouse_button: hid_emulator.MouseButton,
      hid_mouse_button: pasit_hid.PasitHID.MouseButton,
  ):
    """Tests that the mouse click is captured correctly."""
    self.emulator.mouse_click(mouse_button)
    asserts.assert_equal(
        self.hid.get_expected_mouse_events(
            pasit_hid.PasitHID.MouseAction.CLICK, hid_mouse_button
        ),
        self.hid.get_captured_mouse_events(),
    )

  @functools.with_variants(positive=(100, 100), negative=(-100, -100))
  def test_capture_mouse_move(self, x: int, y: int):
    """Tests that the mouse move is captured correctly."""
    self.emulator.mouse_move(x, y)
    asserts.assert_equal(
        self.hid.get_expected_mouse_events(pasit_hid.PasitHID.MouseAction.MOVE),
        self.hid.get_captured_mouse_events(),
    )

  @functools.with_variants(positive=(10,), negative=(-10,))
  def test_capture_mouse_scroll(self, offset: int):
    """Tests that the mouse scroll is captured correctly."""
    self.emulator.mouse_scroll(offset)
    asserts.assert_equal(
        self.hid.get_expected_mouse_events(
            pasit_hid.PasitHID.MouseAction.SCROLL
        ),
        self.hid.get_captured_mouse_events(),
    )


if __name__ == '__main__':
  test_runner.main()
