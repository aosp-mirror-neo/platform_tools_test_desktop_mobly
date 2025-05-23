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

"""Helper functions to abstract the video tester operations into logical UCD operations as a monitor."""

import collections
import logging
import time

from display.utils import compliance_tests_manager
from display.utils import edid_datum
from display.utils import edids_list
from lib.pasit.passport import passport_host
from lib.pasit.passport import passport_video_service_client
from chromiumos.test.lab.api.passport import video_tester_service_pb2


PassportBaseError = passport_host.PassportBaseError
ComplianceTestStatus = video_tester_service_pb2.ComplianceTestStatus


class UcdManager:
  """Manages the connection to the UCD via the video tester service.

  This class provides a simplified interface for connecting to the UCD and
  setting the role of the video tester.
  """

  EXPECTED_SUPPORTED_ROLE = (
      video_tester_service_pb2.Role.ROLE_USBCSOURCE_USBCSINK
  )
  MAX_SUPPORTED_DISPLAY_COUNT = 4
  UCD_DEFAULT_EDIDS: list[edid_datum.EdidDatum] = [
      edids_list.UCD_500_DP1,
      edids_list.UCD_500_DP2,
      edids_list.UCD_500_DP3,
      edids_list.UCD_500_DP4,
  ]

  def __init__(
      self, vsc: passport_video_service_client.PassportVideoServiceClient
  ):
    self._vsc = vsc
    self._is_device_open = False

  def connect_to_ucd(self):
    """Connects to the UCD via the video tester service."""

    # Open the connected UCD to start issuing commands.
    testers = self._vsc.get_connected_video_testers()
    if len(testers) > 1:
      raise PassportBaseError(
          "More than one video tester is already connected to the UCD."
      )
    success = self._vsc.open_video_tester(testers[0].id)
    if not success:
      raise PassportBaseError("Failed to open video tester.")
    self._is_device_open = success

    # Right now, the UCD devices are hardwired to be connected via usb-c on
    # both ends.
    # TODO: b/415014744 - get_roles_available_at_video_tester() is not
    # implemented.
    # When it is, check that EXPECTED_SUPPORTED_ROLE is in the list of roles.
    if not self._vsc.set_role_for_video_tester(self.EXPECTED_SUPPORTED_ROLE):
      raise PassportBaseError("Failed to set role for video tester.")

  def create_and_plug_new_displays(
      self,
      additional_display_count: int,
      displays_edids: list[edid_datum.EdidDatum] | None = None,
  ):
    """Configures new displays simulated through UCD, then plugs them into the DUT by sending an HPD pulse.

    It adds the number of displays to the total number of displays already
    connected to the DUT.

    If `displays_edids` is provided, it will be used to configure the new
    displays. Otherwise, the default EDIDs will be used.
    `additional_display_count` is still needed to know how many displays to
    add, even if `displays_edids` is provided, to validate the number of
    provided EDIDs.

    Args:
      additional_display_count: The number of displays to initialize.
      displays_edids: A list of EDIDs for each display.

    Raises:
      PassportBaseError: If the number of EDIDs does not match the number of
      displays.
    """
    if (
        displays_edids is not None
        and len(displays_edids) != additional_display_count
    ):
      raise PassportBaseError(
          "The number of EDIDs does not match the number of displays."
      )

    stream_infos = self._vsc.get_stream_info_for_all_streams()
    current_connected_displays_count = len(stream_infos)
    total_expected_display_count = (
        current_connected_displays_count + additional_display_count
    )
    logging.info(
        "Total expected display count: %d", total_expected_display_count
    )
    if total_expected_display_count > self.MAX_SUPPORTED_DISPLAY_COUNT:
      raise PassportBaseError(
          "The number of displays is greater than the maximum supported (4)."
      )

    # If no EDIDs are provided, use the default EDIDs, starting from after the
    # current number of connected displays and going up to the total expected
    # number of displays.
    if displays_edids is None:
      displays_edids = self.UCD_DEFAULT_EDIDS[
          current_connected_displays_count:total_expected_display_count
      ]

    if not self._vsc.set_dp_link_capabilities(
        # Set MST to always be true. No downsides.
        mst=True, mst_sink_count=total_expected_display_count
    ):
      raise PassportBaseError("Failed to set DP link capabilities.")

    for i in range(additional_display_count):
      target_stream_id = current_connected_displays_count + i
      if not self._vsc.load_edid_at_stream(
          edid=displays_edids[i].to_bytes(), id_stream=target_stream_id
      ):
        raise PassportBaseError(
            "Failed to load EDID at stream %d" % target_stream_id
        )

    if current_connected_displays_count > 0:
      # if it's already plugged in, an HPD is all we need.
      logging.info("Sending HPD pulse.")
      if not self._vsc.send_hpd_pulse():
        raise PassportBaseError("Failed to send HPD pulse.")
    else:
      logging.info("Attaching to the DUT.")
      if not self._vsc.perform_attach_operation(True):
        raise PassportBaseError("Failed to attach to the DUT.")

    if not self.are_all_screens_on_aux_channel(total_expected_display_count):
      raise PassportBaseError("External displays are not active.")

  def toggle_displays_plug_state(self, should_plug: bool):
    """Plug/Unplug all the displays without destroying their configurations."""
    if not self._vsc.perform_attach_operation(should_plug):
      raise PassportBaseError("Failed to plug/unplug all displays.")

  def are_all_screens_on_aux_channel(
      self, expected_total_display_count: int
  ) -> bool:
    """Waits for all the displays to turn on, checking the aux channel info.

    Args:
      expected_total_display_count: The number of displays to wait for.

    Returns:
      True if all the displays turned on before the timeout.
      The information is retrieved from the aux channel.
    """
    timeout_sec = 20
    start_time = time.time()

    while time.time() - start_time < timeout_sec:
      stream_infos = self._vsc.get_stream_info_for_all_streams()
      if len(stream_infos) != expected_total_display_count:
        continue

      all_screens_on = True
      for stream_info in stream_infos:
        does_have_size = stream_info.hactive > 0 and stream_info.vactive > 1
        does_have_crc = any(crc != 0 for crc in stream_info.crc)
        if not (does_have_size or does_have_crc):
          logging.debug("Stream %s is not active", stream_info)
          all_screens_on = False
          break
      if not all_screens_on:
        continue

      logging.info(
          "All screens are on after %d seconds.", time.time() - start_time
      )
      return True

    logging.info("Timeout waiting for screens to turn on.")
    return False

  def get_screenshot_display(self, display_idx: int) -> bytes:
    """Captures a screenshot from a stream of the open video tester."""
    return self._vsc.get_screenshot_at_stream(display_idx)

  def is_image_not_black(self, image_raw: bytes) -> bool:
    """Checks if the image is not all black."""
    black_threshold = 10  # Values below this are considered "black"
    minimum_non_black_percent = (
        5.0  # Minimum percentage of non-black pixels to consider active
    )
    minimum_unique_values = (
        3  # Minimum number of unique color values for real content
    )

    total_pixels = len(image_raw)
    if not image_raw or total_pixels == 0:
      logging.info("Empty image_raw bytes.")
      return False
    # Count non-black pixels (using a threshold)
    # For most image formats, black is 0 or very close to 0
    non_black = sum(1 for byte in image_raw if byte > black_threshold)
    # Calculate percentage of non-black content
    non_black_percentage = (non_black * 100) / total_pixels

    # Convert samples to a set to eliminate duplicates, then count unique values
    unique_color_count = len(set(image_raw))

    # Screen is showing content if:
    # 1. It has sufficient non-black pixels
    # 2. It has enough variety in color values
    return (
        non_black_percentage > minimum_non_black_percent
        and unique_color_count > minimum_unique_values
    )

  def destroy_the_most_recently_attached_display(self):
    """Destroys the most recently attached display.

    Raises:
      PassportBaseError: If the operation fails or if no displays are currently
      configured.
    """
    configured_displays_count = len(self._vsc.get_stream_info_for_all_streams())
    if configured_displays_count == 0:
      raise PassportBaseError("No displays are currently configured.")

    total_expected_display_count = configured_displays_count - 1
    if not self._vsc.set_dp_link_capabilities(
        mst=bool(total_expected_display_count > 0),
        mst_sink_count=configured_displays_count - 1,
    ):
      raise PassportBaseError("Failed to set DP link capabilities.")

    if not self._vsc.send_hpd_pulse():
      raise PassportBaseError(
          "Failed to send HPD pulse on"
          " destroy_the_most_recently_attached_display."
      )

  def unplug_and_destroy_all_displays(self):
    """Unplug all the displays and destroy them."""
    self.toggle_displays_plug_state(False)
    if not self._vsc.set_dp_link_capabilities(mst=False):
      raise PassportBaseError("Failed to set DP link capabilities.")

  def reset_ucd_displays_state_to_default(self):
    """Resets the displays state."""
    # At reset, bring back the old EDIDs as UCD doesn't reset them
    for i in range(self.MAX_SUPPORTED_DISPLAY_COUNT):
      if len(self.UCD_DEFAULT_EDIDS) > i:
        if not self._vsc.load_edid_at_stream(
            edid=self.UCD_DEFAULT_EDIDS[i].to_bytes(), id_stream=i
        ):
          raise PassportBaseError("Failed to load EDID at stream %d" % i)

    self.unplug_and_destroy_all_displays()

  def run_compliance_tests(
      self,
      group: compliance_tests_manager.TestGroup,
      references: list[str] | None = None,
  ) -> bool:
    """Runs a set of compliance tests.

    If references are provided, it runs specific tests identified by their
    reference numbers within the group.
    If references is None, it runs all tests in the specified group.

    Args:
      group: The TestGroup object containing the tests.
      references: Optional. A list of test reference strings (e.g., ["4.2.1.1",
        "4.2"]) as it can also be partial references. If None, all tests in the
        group are run.

    Returns:
      True if all run tests passed, False otherwise.
    """
    logging.info(
        "\nPreparing to run tests for group: %s (ID: %s)",
        group.name,
        group.group_id,
    )
    if references:
      logging.info("Requested references: %s", references)
      tests = group.get_video_tester_group_and_test_ids(references)
    else:
      logging.info("Requested to run all tests in group %s.", group.name)
      tests = group.get_all_video_tester_tests_in_group()

    results, _ = self._vsc.run_compliance_tests(tests)

    status_counts = collections.defaultdict(int)
    failed_tests = []
    for result in results:
      status = result.status
      status_counts[status] += 1
      if (
          status == ComplianceTestStatus.COMPLIANCE_TEST_FAILED
          or status == ComplianceTestStatus.COMPLIANCE_TEST_ABORTED
      ):
        failed_tests.append(result.test.test_id)

    logging.info("Compliance Test Results:")
    for status, count in status_counts.items():
      status_name = ComplianceTestStatus.Name(status)
      logging.info("%s: %d", status_name, count)

    if failed_tests:
      logging.warning("Failed tests:")
      for test_id in failed_tests:
        test = group.get_test_by_id(test_id)
        if test:
          logging.warning(
              "  - Reference: %s, Description: %s",
              test.reference,
              test.description,
          )
        else:
          logging.warning("  - Test ID: %s (Not found in group)", test_id)

    return not failed_tests

  def disconnect_ucd(self):
    """Disconnects from the UCD via the video tester service."""
    if not self._is_device_open:
      return
    if not self._vsc.close_video_tester():
      raise PassportBaseError("Failed to close video tester.")
    self._is_device_open = False
