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
from lib.utils import retry

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

  def set_dp_video_spec(
      self,
      video_spec: video_tester_service_pb2.VideoSpecification,
      dsc: bool | None = None,
  ):
    """Sets the DP video spec. This is a no-op for non-DP testers."""
    pass

  def get_dp_video_spec(
      self,
  ) -> tuple[video_tester_service_pb2.VideoSpecification | None, bool | None]:
    """Gets the DP video spec. Returns (None, None) for non-DP testers."""
    return None, None

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

  def replug_displays(
      self,
      display_count: int,
      wait_for_active: bool,
      force_mst: bool = False,
      displays_edids: list[edid_datum.EdidDatum] | None = None,
  ):
    """Plugs displays, ensuring a specific configuration.

    This function first unplugs any active displays, then configures the UCD
    to simulate a new set of displays and plugs them into the DUT. This is
    useful for setting a known, clean display state.

    Args:
      display_count: The total number of displays to simulate.
      wait_for_active: If True, the function will wait for the displays to be
        detected and turned on.
      force_mst: If True, forces MST mode. Relevant when a single display is
        plugged in. Otherwise, MST is only enabled if more than one display is
        plugged in.
      displays_edids: A list of EDIDs for each display.

    Raises:
      UcdManagerError: If the number of EDIDs does not match the number of
      displays, or if the number of requested displays is greater than the
      maximum supported.
    """
    logging.debug("Detaching.")
    self._vsc.perform_attach_operation(False)
    if display_count > self.max_supported_displays:
      raise UcdManagerError(
          f"The number of requested displays {display_count} is greater "
          f"than the maximum supported {self.max_supported_displays}."
      )

    if displays_edids:
      if len(displays_edids) < display_count:
        raise UcdManagerError(
            f"The number of provided EDIDs {len(displays_edids)} is less than "
            f"the number of requested displays {display_count}."
        )
      for i in range(display_count):
        self._set_edid(displays_edids[i], i)

    enable_mst = force_mst or bool(display_count > 1)
    self._set_display_caps(enable_mst, display_count)

    logging.debug("Attaching.")
    if not self._vsc.perform_attach_operation(True):
      raise UcdManagerError("Failed to attach to the DUT.")

    if wait_for_active:
      if not self.wait_for_display_count(display_count):
        print_typec_status(self._dut)
        raise UcdManagerError("External displays are not active.")

  def add_hotplug_displays(
      self,
      additional_display_count: int,
      wait_for_active: bool,
      displays_edids: list[edid_datum.EdidDatum] | None = None,
  ):
    """Adds one or more displays to the current configuration via hot-plug.

    This method simulates adding displays to a live system, always enabling MST.
    It adds displays to the existing number of connected displays. It performs
    an attach if no displays are currently connected, otherwise it sends an HPD
    pulse to the DUT.

    Args:
      additional_display_count: The number of displays to add.
      wait_for_active: If True, wait for the displays to become active.
      displays_edids: A list of EDIDs for the new displays.

    Raises:
      UcdManagerError: If the number of EDIDs does not match the number of
      displays, or if the total number of displays exceeds the maximum
      supported.
    """
    if (
        displays_edids is not None
        and len(displays_edids) != additional_display_count
    ):
      raise UcdManagerError(
          "The number of EDIDs does not match the number of displays."
      )

    current_connected_displays_count = len(self.get_active_displays())
    total_expected_display_count = (
        current_connected_displays_count + additional_display_count
    )
    if total_expected_display_count > self.max_supported_displays:
      raise UcdManagerError(
          f"The number of requested displays {total_expected_display_count} is "
          "greater than the maximum supported "
          f"{self.max_supported_displays}."
      )

    if displays_edids:
      for i in range(additional_display_count):
        target_stream_id = current_connected_displays_count + i
        self._set_edid(displays_edids[i], target_stream_id)

    self._set_display_caps(
        is_mst=True, displays_to_set=total_expected_display_count
    )

    if current_connected_displays_count > 0:
      # if it's already plugged in, an HPD is all we need.
      logging.info(
          f"Sending HPD pulse for {total_expected_display_count} displays."
      )
      if not self.send_hpd_pulse():
        raise UcdManagerError("Failed to send HPD pulse.")
      time.sleep(5)
    else:
      logging.info(
          f"Attaching {total_expected_display_count} displays to the DUT."
      )
      logging.debug("Attaching.")
      if not self._vsc.perform_attach_operation(True):
        raise UcdManagerError("Failed to attach to the DUT.")

    if wait_for_active:
      if not self.wait_for_display_count(total_expected_display_count):
        print_typec_status(self._dut)
        raise UcdManagerError("External displays are not active.")

  def unplug_last_display(self, wait_for_active: bool, force_mst: bool = False):
    """Decrements the number of connected displays by one.

    Args:
      wait_for_active: If True, wait for the display count to update.
      force_mst: If True, forces MST mode.

    Raises:
      UcdManagerError: If the operation fails or if no displays are currently
      active.
    """
    active_displays_count = len(self.get_active_displays())
    if active_displays_count == 0:
      raise UcdManagerError("No displays are currently active.")

    remaining_display_count = active_displays_count - 1
    enable_mst = force_mst or bool(remaining_display_count > 1)

    if remaining_display_count > 0:
      self._set_display_caps(enable_mst, remaining_display_count)
      if not self.send_hpd_pulse():
        raise UcdManagerError(
            "Failed to send HPD pulse on unplug_last_display."
        )
    else:
      logging.debug("Detaching.")
      if not self._vsc.perform_attach_operation(False):
        raise UcdManagerError("Failed to detach from the DUT.")

    if wait_for_active:
      if not self.wait_for_display_count(remaining_display_count):
        raise UcdManagerError(
            "Failed to remove the last display. "
            f"Expected {remaining_display_count} displays to be active."
        )

  def unplug_all_displays(self, wait_for_active: bool):
    """Unplugs all displays and destroys their configuration."""
    logging.debug("Detaching.")
    if not self._vsc.perform_attach_operation(False):
      raise UcdManagerError("Failed to detach from the DUT.")

    if wait_for_active:
      if not self.wait_for_display_count(0):
        print_typec_status(self._dut)
        raise UcdManagerError("Monitors are not deactivating.")

  def send_hpd_pulse(self) -> bool:
    """Sends a HotPlug-Detect (HPD) pulse to the DUT.

    This simulates unplugging and quickly replugging the display cable,
    triggering the DUT to re-detect the connected displays.

    Returns:
      True if the HPD pulse was sent successfully.
    """
    logging.debug("Sending HPD pulse.")
    return self._vsc.send_hpd_pulse()

  def wait_for_display_count(
      self, expected_display_count: int, timeout_sec: int = 20
  ) -> bool:
    """Waits for a specific number of displays to become active.

    This method repeatedly checks the number of active displays until it
    matches the expected count or a timeout is reached.

    Args:
      expected_display_count: The exact number of active displays to wait for.
      timeout_sec: The timeout in seconds.

    Returns:
      True if the expected number of displays became active within the timeout,
      False otherwise.
    """

    class _DisplayCountError(Exception):
      """Raised when the display count does not match."""

    delay_sec = 5
    max_tries = timeout_sec // delay_sec
    start_time = time.time()
    last_active_displays_count = 0

    def _check_display_count():
      nonlocal last_active_displays_count
      active_displays_count = len(self.get_active_displays())
      last_active_displays_count = active_displays_count
      if active_displays_count != expected_display_count:
        logging.debug(
            "Waiting for %d active displays, found %d.",
            expected_display_count,
            active_displays_count,
        )
        raise _DisplayCountError(
            f"Expected {expected_display_count}, found {active_displays_count}"
        )

    try:
      retry.retry(
          _check_display_count,
          policy=retry.RetryPolicy(
              max_tries=max_tries, delay_seconds=delay_sec
          ),
          exceptions=(_DisplayCountError,),
      )
      logging.info(
          "%d displays are active after ~%.1fs.",
          expected_display_count,
          time.time() - start_time,
      )
      return True
    except _DisplayCountError:
      logging.error(
          "Timeout waiting for %d active displays, found %d.",
          expected_display_count,
          last_active_displays_count,
      )
      return False

  def get_active_displays(
      self,
  ) -> list[
      passport_video_service_client.video_tester_service_pb2.StreamInfoVideoTester
  ]:
    """Returns a list of all active display streams."""
    streams = self._vsc.get_stream_info_for_all_streams()
    active_displays = []
    for stream in streams:
      has_video = stream.hactive > 0 and stream.vactive > 1
      has_crc = any(crc != 0 for crc in stream.crc)
      if has_video or has_crc:
        active_displays.append(stream)
    return active_displays

  def get_display_screenshot(self, display_idx: int) -> bytes:
    """Captures a screenshot from a specific display.

    Args:
      display_idx: The 0-based index of the display to capture.

    Returns:
      The screenshot as a byte string.
    """
    return self._vsc.get_screenshot_at_stream(display_idx)

  def reset_ucd_displays_state_to_default(self):
    """Resets the displays state."""
    # At reset, bring back the old EDIDs as UCD doesn't reset them
    logging.info("Resetting UCD displays state to default.")
    for i in range(self.max_supported_displays):
      self._set_edid(self._get_default_edids()[i], i)

    self.unplug_all_displays(wait_for_active=True)

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

  def __init__(
      self,
      vsc: passport_video_service_client.PassportVideoServiceClient,
      dut: pasit_device.PasitDevice,
  ):
    super().__init__(vsc, dut)
    # Default settings for DP 1.4.
    self._video_spec = (
        video_tester_service_pb2.VideoSpecification.VIDEO_SPECIFICATION_DP_1_4
    )
    self._dsc = True

  def set_dp_video_spec(
      self,
      video_spec: video_tester_service_pb2.VideoSpecification,
      dsc: bool | None = None,
  ):
    logging.debug(
        "Setting DP video spec to %s, dsc: %s",
        video_tester_service_pb2.VideoSpecification.Name(video_spec),
        dsc,
    )
    self._video_spec = video_spec
    self._dsc = dsc

  def get_dp_video_spec(
      self,
  ) -> tuple[video_tester_service_pb2.VideoSpecification | None, bool | None]:
    return self._video_spec, self._dsc

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
    if displays_to_set < 1:
      raise UcdManagerError(
          "There is no need to set display capabilities if there are %d"
          " display. Just go ahead and detach instead." % displays_to_set
      )

    logging.debug(
        "Setting DP link capabilities with is_mst: %s, displays_to_set: %d,"
        " video_spec: %s, dsc: %s",
        is_mst,
        displays_to_set,
        video_tester_service_pb2.VideoSpecification.Name(self._video_spec),
        self._dsc,
    )
    if not self._vsc.set_dp_link_capabilities(
        mst=is_mst,
        ss_sbm=is_mst if displays_to_set else None,
        mst_sink_count=displays_to_set,
        video_spec=self._video_spec,
        dsc=self._dsc,
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
