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

import abc
import collections
import logging
import time

from chromiumos.test.lab.api.passport import video_tester_service_pb2
from display.utils import compliance_tests_manager
from display.utils import edid_datum
from display.utils import edids_list
from display.utils import interface_types
from lib.pasit import pasit_device
from lib.pasit.passport import passport_video_service_client

ComplianceTestStatus = video_tester_service_pb2.ComplianceTestStatus


# ADB shell commands to get the typec status of the DUT for each physical port.
# They're nice to print when we fail a plug/unplug operation.
def print_typec_status(dut: pasit_device.PasitDevice):
  for i in range(4):
    cmd = f"ectool typecstatus {i}"
    try:
      logging.info(dut.shell(cmd.split()).decode("utf-8", errors="ignore"))
    except:
      break


class UcdManagerError(Exception):
  """Error class for UcdManager."""


class UcdManager(abc.ABC):
  """Manages the connection to the UCD via the video tester service.

  This class provides a simplified interface for connecting to the UCD and
  setting the role of the video tester.
  """

  dut: pasit_device.PasitDevice

  def __init__(
      self,
      vsc: passport_video_service_client.PassportVideoServiceClient,
      dut: pasit_device.PasitDevice,
  ):
    self._vsc = vsc
    self._dut = dut

  @property
  @abc.abstractmethod
  def interface_type(self) -> interface_types.InterfaceType:
    pass

  @property
  @abc.abstractmethod
  def max_supported_displays(self) -> int:
    pass

  @abc.abstractmethod
  def set_role(self) -> None:
    pass

  @abc.abstractmethod
  def _get_default_edids(self) -> list[edid_datum.EdidDatum]:
    pass

  @abc.abstractmethod
  def _set_display_caps(self, is_mst: bool, displays_to_set: int) -> None:
    pass

  @abc.abstractmethod
  def _set_edid(self, edid: edid_datum.EdidDatum, stream_id: int) -> None:
    pass

  @staticmethod
  def connect_to_ucd(
      vsc: passport_video_service_client.PassportVideoServiceClient,
      dut: pasit_device.PasitDevice,
  ) -> "UcdManager":
    # Open the connected UCD to start issuing commands.
    testers = vsc.get_connected_video_testers()
    if not testers or len(testers) > 1:
      raise UcdManagerError(
          "Expected 1 video tester to be connected to the UCD, but found"
          f" {len(testers)}."
      )
    tester = testers[0]

    manager: "UcdManager"
    if "500" in tester.name:
      manager = Ucd500Manager(vsc, dut)
    elif "422" in tester.name:
      manager = Ucd422Manager(vsc, dut)
    else:
      raise UcdManagerError(
          f"Unsupported UCD model: {tester.name}. Only UCD500 and UCD422 are"
          " supported."
      )

    success = vsc.open_video_tester(tester.id)
    if not success:
      raise UcdManagerError("Failed to open video tester.")

    try:
      manager.set_role()
    except Exception as e:
      vsc.close_video_tester()
      raise UcdManagerError(f"Failed to set role for {tester.name}: {e}") from e

    return manager

  def set_total_displays_count(
      self,
      total_display_count: int,
      displays_edids: list[edid_datum.EdidDatum] | None = None,
  ):
    """Sets the total number of displays to be simulated by the UCD and plugs them into the DUT.

    This function configures the UCD to simulate a specific number of displays
    and plugs them into the DUT. It does not wait for the displays to be
    detected or turned on.

    Args:
      total_display_count: The total number of displays to simulate.
      displays_edids: A list of EDIDs for each display.

    Raises:
      UcdManagerError: If the number of EDIDs does not match the number of
      displays, or if the number of requested displays is greater than the
      maximum supported.
    """
    self._vsc.perform_attach_operation(False)

    if total_display_count > self.max_supported_displays:
      raise UcdManagerError(
          f"The number of requested displays {total_display_count} is greater "
          f"than the maximum supported {self.max_supported_displays}."
      )

    if not displays_edids:
      displays_edids = self._get_default_edids()

    if len(displays_edids) < total_display_count:
      raise UcdManagerError(
          f"The number of provided EDIDs {len(displays_edids)} is less than "
          f"the number of requested displays {total_display_count}."
      )

    enable_mst = bool(total_display_count > 1)
    self._set_display_caps(enable_mst, total_display_count)

    for i in range(total_display_count):
      self._set_edid(displays_edids[i], i)

    if not self._vsc.perform_attach_operation(True):
      raise UcdManagerError("Failed to attach to the DUT.")

  def plug_additional_displays_to_active_displays(
      self,
      additional_display_count: int,
      force_mst: bool = False,
      displays_edids: list[edid_datum.EdidDatum] | None = None,
  ):
    """Configures new displays simulated through UCD, then plugs them into the DUT by sending an HPD pulse.

    This function adds a specified number of displays to the existing
    configuration, which means that it appends new displays to the current
    active displays. It then plugs them into the DUT and waits for them to be
    detected and turned on.

    If `displays_edids` is provided, it will be used to configure the new
    displays. Otherwise, the default EDIDs will be used.
    `additional_display_count` is still needed to know how many displays to
    add, even if `displays_edids` is provided, to validate the number of
    provided EDIDs.

    Args:
      additional_display_count: The number of displays to add.
      displays_edids: A list of EDIDs for each display.

    Raises:
      UcdManagerError: If the number of EDIDs does not match the number of
      displays, or if the number of requested displays is greater than the
      maximum supported.
    """
    if (
        displays_edids is not None
        and len(displays_edids) != additional_display_count
    ):
      raise UcdManagerError(
          "The number of EDIDs does not match the number of displays."
      )

    current_connected_displays_count = len(self.get_valid_streams())
    total_expected_display_count = (
        current_connected_displays_count + additional_display_count
    )
    if total_expected_display_count > self.max_supported_displays:
      raise UcdManagerError(
          f"The number of requested displays {total_expected_display_count} is "
          "greater than the maximum supported "
          f"{self.max_supported_displays}."
      )

    enable_mst = force_mst or bool(total_expected_display_count > 1)
    self._set_display_caps(enable_mst, total_expected_display_count)

    if displays_edids is not None:
      for i in range(additional_display_count):
        target_stream_id = current_connected_displays_count + i
        self._set_edid(displays_edids[i], target_stream_id)

    if current_connected_displays_count > 0:
      # if it's already plugged in, an HPD is all we need.
      logging.info(
          f"Sending HPD pulse for {total_expected_display_count} displays with"
          f" MST={enable_mst}."
      )
      if not self._vsc.send_hpd_pulse():
        raise UcdManagerError("Failed to send HPD pulse.")
      time.sleep(5)
    else:
      logging.info(
          f"Attaching {total_expected_display_count} displays to the DUT with"
          f" MST={enable_mst}."
      )
      if not self._vsc.perform_attach_operation(True):
        raise UcdManagerError("Failed to attach to the DUT.")

    if not self.are_displays_reporting_stream_info(
        total_expected_display_count
    ):
      print_typec_status(self._dut)
      raise UcdManagerError("External displays are not active.")

  def are_displays_reporting_stream_info(
      self, expected_total_display_count: int
  ) -> bool:
    """Waits for the exact number of expected displays to turn on, checking the aux channel info.

    Args:
      expected_total_display_count: The exact number of displays to wait for.

    Returns:
      True if the exact number of displays turned on before the timeout.
      The information is retrieved from the aux channel.
    """
    timeout_sec = 20
    start_time = time.time()

    valid_streams_count = 0
    while time.time() - start_time < timeout_sec:
      valid_streams_count = len(self.get_valid_streams())
      if valid_streams_count != expected_total_display_count:
        logging.debug(
            f"Waiting for {expected_total_display_count} displays to report"
            f" stream info. Finding {valid_streams_count} instead"
        )
        time.sleep(5)
        continue

      logging.info(
          f"{expected_total_display_count} displays are reported after ~"
          f"{time.time() - start_time:.1f}s."
      )
      return True

    logging.info(
        f"Timeout waiting for {expected_total_display_count} displays to report"
        f" stream info. Finding {valid_streams_count} instead"
    )
    return False

  def get_valid_streams(
      self,
  ) -> list[
      passport_video_service_client.video_tester_service_pb2.StreamInfoVideoTester
  ]:
    """Returns all the valid streams from the stream info list."""
    streams = self._vsc.get_stream_info_for_all_streams()
    valid_streams = []
    for stream in streams:
      does_have_size = stream.hactive > 0 and stream.vactive > 1
      does_have_crc = any(crc != 0 for crc in stream.crc)
      if does_have_size or does_have_crc:
        valid_streams.append(stream)
    return valid_streams

  def get_screenshot_display(self, display_idx: int) -> bytes:
    """Captures a screenshot from a stream of the open video tester."""
    return self._vsc.get_screenshot_at_stream(display_idx)

  def destroy_the_most_recently_attached_display(self, force_mst: bool = False):
    """Destroys the most recently attached display.

    Raises:
      UcdManagerError: If the operation fails or if no displays are currently
      configured.
    """
    configured_displays_count = len(self._vsc.get_stream_info_for_all_streams())
    if configured_displays_count == 0:
      raise UcdManagerError("No displays are currently configured.")

    total_expected_display_count = configured_displays_count - 1
    enable_mst = force_mst or bool(total_expected_display_count > 1)
    self._set_display_caps(enable_mst, total_expected_display_count)

    if total_expected_display_count > 0:
      if not self._vsc.send_hpd_pulse():
        raise UcdManagerError(
            "Failed to send HPD pulse on"
            " destroy_the_most_recently_attached_display."
        )
    else:
      if not self._vsc.perform_attach_operation(False):
        raise UcdManagerError("Failed to detach from the DUT.")

    if not self.are_displays_reporting_stream_info(
        total_expected_display_count
    ):
      raise UcdManagerError(
          "Failed to destroy the most recently attached display. "
          f"Expected {total_expected_display_count} displays to be active."
      )

  def unplug_and_destroy_all_displays(self):
    """Unplug all the displays and destroy them."""
    self._set_display_caps(is_mst=False, displays_to_set=0)
    logging.debug("Detaching...")
    if not self._vsc.perform_attach_operation(False):
      raise UcdManagerError("Failed to detach from the DUT.")
    if not self.are_displays_reporting_stream_info(0):
      print_typec_status(self._dut)
      raise UcdManagerError("Monitors are not deactivating.")

  def reset_ucd_displays_state_to_default(self):
    """Resets the displays state."""
    # At reset, bring back the old EDIDs as UCD doesn't reset them
    logging.info("Resetting UCD displays state to default.")
    for i in range(self.max_supported_displays):
      self._set_edid(self._get_default_edids()[i], i)

    self.unplug_and_destroy_all_displays()

  def run_compliance_tests(
      self,
      board: str,
      model: str,
      group: compliance_tests_manager.TestGroup,
      references: list[str] | None = None,
  ) -> bool:
    """Runs a set of compliance tests.

    If references are provided, it runs specific tests identified by their
    reference numbers within the group.
    If references is None, it runs all tests in the specified group.

    Args:
      board: The board of the DUT (e.g., "brya", "fatcat").
      model: The model of the DUT (e.g., "redrix", "mithrax").
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

    results, _ = self._vsc.run_compliance_tests(tests, board, model)

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
    self._vsc.close_video_tester()


class Ucd500Manager(UcdManager):
  """UCD 500 is the DP Tester Device."""

  @property
  def interface_type(self) -> interface_types.InterfaceType:
    return interface_types.InterfaceType.DP

  @property
  def max_supported_displays(self) -> int:
    return 4

  def set_role(self) -> None:
    # Right now, the UCD devices are hardwired to be connected via usb-c on
    # both ends.
    if not self._vsc.set_role_for_video_tester(
        video_tester_service_pb2.Role.ROLE_USBCSOURCE_USBCSINK
    ):
      raise UcdManagerError("Failed to set role for video tester.")

  def _get_default_edids(self) -> list[edid_datum.EdidDatum]:
    return [
        edids_list.UCD_500_DP1,
        edids_list.UCD_500_DP2,
        edids_list.UCD_500_DP3,
        edids_list.UCD_500_DP4,
    ]

  def _set_display_caps(self, is_mst: bool, displays_to_set: int) -> None:
    logging.debug(f"is_mst: {is_mst}, displays_to_set: {displays_to_set}")
    if not self._vsc.set_dp_link_capabilities(
        mst=is_mst,
        ss_sbm=is_mst if displays_to_set else None,
        mst_sink_count=displays_to_set,
    ):
      raise UcdManagerError("Failed to set DP link capabilities.")

  def _set_edid(self, edid: edid_datum.EdidDatum, stream_id: int) -> None:
    if edid.interface_type != interface_types.InterfaceType.DP:
      raise UcdManagerError(
          "EDID is not a DP EDID. It's a %s EDID." % edid.interface_type.value
      )
    if not self._vsc.load_edid_at_stream(
        edid=edid.to_bytes(), id_stream=stream_id
    ):
      raise UcdManagerError("Failed to load EDID at stream %d" % stream_id)


class Ucd422Manager(UcdManager):
  """UCD 422 is the HDMI Tester Device."""

  @property
  def interface_type(self) -> interface_types.InterfaceType:
    return interface_types.InterfaceType.HDMI

  @property
  def max_supported_displays(self) -> int:
    return 1

  def set_role(self) -> None:
    if not self._vsc.set_role_for_video_tester(
        video_tester_service_pb2.Role.ROLE_HDMISOURCE_HDMISINK
    ):
      raise UcdManagerError("Failed to set role for video tester.")

  def _get_default_edids(self) -> list[edid_datum.EdidDatum]:
    return [edids_list.UCD_422_HDMI]

  def _set_display_caps(self, is_mst: bool, displays_to_set: int) -> None:
    if displays_to_set > self.max_supported_displays:
      raise UcdManagerError(
          f"HDMI doesn't support more than one display. {displays_to_set} "
          "displays were requested."
      )
    # For HDMI < 2.1, no fields need to be set.
    # However, for HDMI 2.1, frl_mode is required.
    # None of the current AL devices support HDMI 2.1.

  def _set_edid(self, edid: edid_datum.EdidDatum, stream_id: int) -> None:
    if edid.interface_type != interface_types.InterfaceType.HDMI:
      raise UcdManagerError(
          "EDID is not an HDMI EDID. It's a %s EDID."
          % edid.interface_type.value
      )
    if not self._vsc.load_edid_at_stream(
        edid=edid.to_bytes(), id_stream=stream_id
    ):
      raise UcdManagerError("Failed to load EDID at stream %d" % stream_id)
