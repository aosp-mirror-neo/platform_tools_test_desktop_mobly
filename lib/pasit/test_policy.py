from lib.utils import retry


class CameraTestPolicy:
  DETECT_EXTERNAL_CAMERA_DEVICES_RETRY_POLICY = retry.RetryPolicy(
      max_tries=10, delay_seconds=1
  )
  CAMERA_APP_IS_USING_DEVICE_RETRY_POLICY = retry.RetryPolicy(
      max_tries=10, delay_seconds=1
  )
  FIND_CAMERA_CAPTURED_FILES_RETRY_POLICY = retry.RetryPolicy(
      max_tries=10, delay_seconds=1
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


class StorageTestPolicy:
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


class HIDTestPolicy:
  FIND_NEW_SCREENSHOTS_RETRY_POLICY = retry.RetryPolicy(
      max_tries=10,
      delay_seconds=1,
  )


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
