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

"""Test policies for PASIT tests.

These policies are used to keep timeouts and other parameters controlling the
behavior of the tests in a single location for easier discovery and
modification.
"""

from lib.pasit import pasit_test_config
from lib.utils import retry


class CameraTestPolicy:
  DETECT_EXTERNAL_CAMERA_DEVICES_RETRY_POLICY = retry.RetryPolicy(
      max_tries=30, delay_seconds=2
  )
  CAMERA_APP_IS_USING_DEVICE_RETRY_POLICY = retry.RetryPolicy(
      max_tries=10, delay_seconds=1
  )
  FIND_CAMERA_CAPTURED_FILES_RETRY_POLICY = retry.RetryPolicy(
      max_tries=10, delay_seconds=1
  )
  VERIFY_EXTERNAL_CAMERA_COLOR_RETRY_POLICY = retry.RetryPolicy(
      max_tries=3, delay_seconds=1
  )


class DisplayTestPolicy:
  EXPECTED_DISPLAY_COUNT_RETRY_POLICY = retry.RetryPolicy(
      max_tries=15,
      delay_seconds=2,
  )
  MATCH_COLOR_RETRY_POLICY = retry.RetryPolicy(
      max_tries=3,
      delay_seconds=0,
  )
  MAP_DISPLAYS_TO_CAMERAS_RETRY_POLICY = retry.RetryPolicy(
      max_tries=3,
      delay_seconds=10,
  )
  DISPLAY_RESOLUTION_CHANGED_RETRY_POLICY = retry.RetryPolicy(
      max_tries=3,
      delay_seconds=5,
  )
  STABLE_ID_POLLING_INTERVAL_SECONDS = 2
  STABLE_ID_REQUIRED_DURATION_SECONDS = 10
  STABLE_ID_TIMEOUT_SECONDS = 40
  REBOOT_POLICY = pasit_test_config.RebootPolicy.ON_FAIL


class StorageTestPolicy:
  """Test policies for Storage tests."""

  EXTERNAL_STORAGE_DETECTED_RETRY_POLICY = retry.RetryPolicy(
      max_tries=30,
      delay_seconds=2,
  )
  EXTERNAL_STORAGE_MOUNTED_RETRY_POLICY = retry.RetryPolicy(
      max_tries=15,
      delay_seconds=2,
  )
  EXTERNAL_STORAGE_UNMOUNTED_RETRY_POLICY = retry.RetryPolicy(
      max_tries=15,
      delay_seconds=2,
  )
  EXTERNAL_STORAGE_BLOCK_VERIFICATION_RETRY_POLICY = retry.RetryPolicy(
      max_tries=20,
      delay_seconds=2,
  )


class HIDTestPolicy:
  """Test policies for HID tests."""

  FIND_NEW_SCREENSHOTS_RETRY_POLICY = retry.RetryPolicy(
      max_tries=10,
      delay_seconds=1,
  )
  DETECT_HID_EMULATOR_RETRY_POLICY = retry.RetryPolicy(
      max_tries=20,
      delay_seconds=3,
  )
  DETECT_EXTERNAL_HID_DEVICES_RETRY_POLICY = retry.RetryPolicy(
      max_tries=30,
      delay_seconds=2,
  )
  DETECT_UNPLUGGED_HID_DEVICES_RETRY_POLICY = retry.RetryPolicy(
      max_tries=5,
      delay_seconds=2,
  )
  NUM_HID_DEVICES_EXPECTED = 3
  STABLE_POLLING_INTERVAL_SECONDS = 2
  STABLE_REQUIRED_DURATION_SECONDS = 10
  STABLE_TIMEOUT_SECONDS = 60


class DeviceTestPolicy:
  WAIT_FOR_DEVICE_ONLINE_RETRY_POLICY = retry.RetryPolicy(
      max_tries=30,
      delay_seconds=4,
  )
  WAIT_FOR_DEVICE_OFFLINE_RETRY_POLICY = retry.RetryPolicy(
      max_tries=20,
      delay_seconds=2,
  )


class NetworkTestPolicy:
  DETECT_EXTERNAL_NETWORK_DEVICES_RETRY_POLICY = retry.RetryPolicy(
      max_tries=30,
      delay_seconds=2,
  )
  DETECT_NETWORK_CABLE_CONNECTED_RETRY_POLICY = retry.RetryPolicy(
      max_tries=15,
      delay_seconds=2,
  )
  DETECT_NETWORK_INTERNET_CONNECTED_RETRY_POLICY = retry.RetryPolicy(
      max_tries=10,
      delay_seconds=2,
  )


class DockTestPolicy:
  """Test policies for Dock tests."""

  DOCK_POWER_DETECTED_RETRY_POLICY = retry.RetryPolicy(
      max_tries=10,
      delay_seconds=2,
  )
