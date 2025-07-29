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

"""A smoke test that validates PASIT periphal functionality.

These are intended to be the most basic tests that we can run to validate that
the testbed setup is and that all the connections are working.

It is still prone to failure due to things outside of the testbed, however,
these are meant to be the first tests to run when setting up a new testbed or
when a testbed is suspected to be in a bad state to help with debugging.
"""

import logging

from chromiumos.test.lab.api import pasit_host_pb2
from google.protobuf import json_format
from lib.pasit import display_helper
from lib.pasit import display_painter
from lib.pasit import pasit_camera
from lib.pasit import pasit_display
from lib.pasit import pasit_hid
from lib.pasit import pasit_storage
from lib.pasit import pasit_test
from lib.pasit.passport import utils
from lib.utils import retry
from mobly import asserts
from mobly import signals
from mobly import test_runner


class PasitPeripheralTest(pasit_test.PasitTestClass):

  display: pasit_display.PasitDisplay

  def _get_test_name(
      self, device_type: str, device_id: str, tag: str | None = None
  ) -> str:
    """Get the test name for the given device type and id."""
    path = '_' + tag.lower() if tag else ''
    return f'test_{device_type}{path}_device_{device_id}'

  def _storage_test_logic(self, device_id: str):
    """Tests that we can activate and detect a specific storage device."""
    storage = self.create(pasit_storage)
    logging.info('Testing storage device: %s', device_id)
    self.passport_host.activate_device_by_id(device_id)
    mount_point = retry.retry(
        storage.get_external_mount_point,
        until=lambda mount_point: mount_point,
        max_tries=10,
    )
    logging.info('Found storage mount point: %s', mount_point)
    asserts.assert_true(
        mount_point,
        'No external storage device found.',
    )

  def _camera_test_logic(self, device_id: str):
    """Tests that we can activate and detect a specific camera device."""
    camera = self.create(pasit_camera)
    camera_devices = camera.get_connected_cameras()

    logging.info('Testing camera device: %s', device_id)
    self.passport_host.activate_device_by_id(device_id)
    newly_plugged_cameras = retry.retry(
        lambda: self._get_newly_plugged_cameras(camera, camera_devices),
        until=lambda result: result,
    )
    asserts.assert_true(
        newly_plugged_cameras,
        'No camera devices were detected as being plugged in after activation.',
    )

  def _display_count_test_logic(self, device_id: str, tag: str | None):
    """Tests that we can activate and detect a specific display device and verify count."""
    self._test_display(device_id, False, tag)

  def _display_mapping_test_logic(self, device_id: str, tag: str | None):
    """Tests that we can activate and detect a specific display device and verify mapping."""
    self._test_display(device_id, True, tag)

  def _test_display(
      self, device_id: str, test_display_mapping: bool, tag: str | None
  ) -> None:
    asserts.skip_if(
        not self.passport_host.is_device_type_present(
            pasit_test.PasitTestClass.DEVICE_TYPE_MONITOR,
            tag,
        ),
        'Display device is not present in the topology.',
    )
    self.display = self.create(pasit_display)
    logging.info(
        'Testing display device: %s with %s path',
        device_id,
        tag if tag else 'default',
    )
    self.passport_host.activate_device_by_id(device_id, tag)
    expected_display_count = 2  # 1 internal + 1 external
    if tag == display_helper.DisplayPaths.DAISY_CHAIN.value:
      # 1 internal + 2 external for daisy chain there is no way to connect just
      # 1 external display in daisy chain mode.
      expected_display_count = 3
    display_count = retry.retry(
        self.display.get_display_count,
        until=lambda count: count == expected_display_count,
        max_tries=10,
        delay_seconds=2,
    )
    asserts.assert_equal(
        display_count,
        expected_display_count,
        f'Display count is not {expected_display_count}, expected 1 internal +'
        f' {expected_display_count - 1} external displays.',
    )
    logging.info('Display count is %d', display_count)
    if test_display_mapping:
      self._check_display_mapping()

  def _hid_test_logic(self, device_id: str):
    """Tests that we can activate and detect a specific HID emulator."""
    hid_client = self.passport_host.hid_client
    if hid_client is None:
      raise signals.TestError('Passport does not have a HID client.')
    hid = self.create(pasit_hid)
    default_hid = hid.get_hid_devices()

    logging.info('Testing HID device: %s', device_id)
    self.passport_host.activate_device_by_id(device_id)
    passport_hid_devices = hid_client.get_hid_devices()
    logging.info('Passport HID devices: %s', passport_hid_devices)
    asserts.assert_true(
        passport_hid_devices,
        'Expected passport to have an HID device after activation.',
    )
    updated_hid_devices = hid.get_hid_devices()
    new_hid_devices = [
        dev for dev in updated_hid_devices if dev not in default_hid
    ]
    logging.info('New DUT HID devices: %s', new_hid_devices)
    asserts.assert_equal(
        len(new_hid_devices),
        3,
        'Expected DUT to have 3 new HID devices after activation of HID'
        ' emulator.',
    )

  def _get_newly_plugged_cameras(
      self, camera: pasit_camera.PasitCamera, existing_camera_devices: list[str]
  ) -> list[str]:
    """Returns the newly plugged in cameras."""
    camera_devices = camera.get_connected_cameras()
    return [
        device
        for device in camera_devices
        if device not in existing_camera_devices
    ]

  def _check_display_mapping(self) -> None:
    """Checks that the display mapping is correct."""
    painter = self.create(display_painter)
    helper = display_helper.DisplayHelper(
        self.passport_host,
        self.display,
        painter,
        self.current_test_info.output_path,
    )
    logging.info('Trying to map displays to cameras...')
    mapping = retry.retry(
        helper.map_displays_to_cameras,
        max_tries=3,
        delay_seconds=10,
        exceptions=(signals.TestError,),
    )
    logging.info('Mapped displays to cameras: %s', mapping)
    asserts.assert_equal(
        len(mapping), 2, 'Unexpected number of displays to camera mappings.'
    )

  def _get_topology(self) -> pasit_host_pb2.PasitHost:
    """Reads and parses the topology from the test config."""
    # pre-run is run before setup_class, so we need to read from the config
    # instead of from the passport host.
    host_cfg = self.controller_configs.get('PassportHost')
    if not host_cfg:
      raise signals.TestError(
          'No PassportHost found for controller config, this test requires a'
          ' Passport Configuration.'
      )
    topology_cfg = host_cfg[0].get('host_topology')
    if not topology_cfg:
      raise signals.TestError(
          'No topology found, this test requires a topology.'
      )
    return json_format.ParseDict(topology_cfg, pasit_host_pb2.PasitHost())

  def _get_devices_from_topology(
      self,
      topology: pasit_host_pb2.PasitHost,
      device_type: pasit_host_pb2.PasitHost.Device.Type,
  ) -> list[tuple[str]]:
    """Gets a list of device ids from the topology for a given device type."""
    return [
        (device.id,)
        for device in topology.devices
        if device.type == device_type
    ]

  def _generate_storage_tests(self, topology: pasit_host_pb2.PasitHost) -> None:
    """Generates tests for storage devices."""
    storage_devices = self._get_devices_from_topology(
        topology, self.DEVICE_TYPE_STORAGE
    )
    if storage_devices:
      self.generate_tests(
          test_logic=self._storage_test_logic,
          name_func=lambda id: self._get_test_name('storage', id),
          arg_sets=storage_devices,
      )

  def _generate_camera_tests(self, topology: pasit_host_pb2.PasitHost) -> None:
    """Generates tests for camera devices."""
    camera_devices = self._get_devices_from_topology(
        topology, self.DEVICE_TYPE_CAMERA
    )
    if camera_devices:
      self.generate_tests(
          test_logic=self._camera_test_logic,
          name_func=lambda id: self._get_test_name('camera', id),
          arg_sets=camera_devices,
      )

  def _generate_display_tests(self, topology: pasit_host_pb2.PasitHost) -> None:
    """Generates tests for display devices."""
    display_count_test_devices = []
    display_mapping_devices = []
    display_devices = [
        d for d in topology.devices if d.type == self.DEVICE_TYPE_MONITOR
    ]

    # for each display device, generate the appropriate tests for it.
    # rules to generate test cases are
    # - generate display count test for all displays and paths except daisy
    #  chain where we only test the full chain.
    # - display mapping test generate for dock and dockless only, single
    #   display at a time, don't test on EDID devices
    for device in display_devices:
      # leaf node tags are used to determine what paths can be used to enable a display
      tags = utils.get_child_tags(
          topology,
          device.id,
          [item.value for item in display_helper.DisplayPaths],
      )
      for tag in tags:
        if (
            tag == display_helper.DisplayPaths.DAISY_CHAIN.value
            and not utils.is_leaf_node(topology, device.id)
        ):
          # for daisy chain, we only test the full chain, so skip all the
          # intermediate displays and only test the leaf node.
          continue
        # generate display count tests
        display_count_test_devices.append((device.id, tag))
        if (
            not utils.is_edid(topology, device.id)
            and tag != display_helper.DisplayPaths.DAISY_CHAIN.value
        ):
          # generate display mapping tests for dock and dockless only, ignoring
          # EDID devices and daisy chain
          display_mapping_devices.append((device.id, tag))

    if display_count_test_devices:
      self.generate_tests(
          test_logic=self._display_count_test_logic,
          name_func=lambda id, tag: self._get_test_name(
              'display_count', id, tag
          ),
          arg_sets=display_count_test_devices,
      )
    if display_mapping_devices:
      self.generate_tests(
          test_logic=self._display_mapping_test_logic,
          name_func=lambda id, tag: self._get_test_name(
              'display_mapping', id, tag
          ),
          arg_sets=display_mapping_devices,
      )

  def _generate_hid_tests(self, topology: pasit_host_pb2.PasitHost) -> None:
    """Generates tests for HID devices."""
    hid_devices = self._get_devices_from_topology(
        topology, self.DEVICE_TYPE_HID
    )
    if hid_devices:
      self.generate_tests(
          test_logic=self._hid_test_logic,
          name_func=lambda id: self._get_test_name('hid', id),
          arg_sets=hid_devices,
      )

  def pre_run(self):
    """Generate tests for each test case based on the topology."""
    topology = self._get_topology()
    self._generate_storage_tests(topology)
    self._generate_camera_tests(topology)
    self._generate_display_tests(topology)
    self._generate_hid_tests(topology)


if __name__ == '__main__':
  test_runner.main()
