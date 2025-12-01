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

import logging
import os
import sys
import unittest
from unittest import mock
from chromiumos.test.lab.api import pasit_host_pb2
from lib.pasit import peripheral_connector
from lib.pasit.passport import passport_host
from lib.utils import functools
import yaml


NOT_FOUND_ERROR_REGEX = 'Peripheral path .* not found in topology'
NOT_ENOUGH_PERIPHERALS_ERROR_REGEX = (
    'Peripheral count .* is less than minimum required count .*'
)

TESTDATA_PATH = os.path.join(
    os.path.dirname(os.path.abspath(sys.argv[0])),
    'testdata',
)


@functools.generate_tests
class PeripheralConnectorTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    # Setup logging to stdout so we can see the logs in the test results.
    # Note it must be to stdout and not stderr, otherwise the logs interfere
    # with the parsing of the test results.
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    patchers = [
        mock.patch(
            'lib.pasit.passport.passport_host.PassportHost._connect_to_service',
        ),
        mock.patch(
            'lib.pasit.passport.passport_host.PassportHost._validate_topology_switches',
        ),
        mock.patch(
            'lib.pasit.passport.passport_host.PassportHost._activate_usb_testers',
        ),
        mock.patch(
            'lib.pasit.passport.passport_host.PassportHost._setup_ip_power_clients',
        ),
    ]
    for patcher in patchers:
      patcher.start()
      self.addCleanup(patcher.stop)

  def _get_test_data(self, file_name):
    file_path = os.path.join(TESTDATA_PATH, file_name)
    with open(file_path, 'r') as f:
      return yaml.safe_load(f)

  def _create_peripheral_connector(self, filename):
    """Creates an instance of PeripheralConnector with a mocked passport_host."""
    config = self._get_test_data(filename)
    testbed_config = config.get('TestBeds', [{}])[0]
    self.assertTrue(
        testbed_config, 'TestBeds not found in config for file {filename}.'
    )
    controllers = testbed_config.get('Controllers')
    self.assertTrue(
        controllers, 'Controllers not found in config for file {filename}.'
    )
    passport_config = controllers.get('PassportHost')
    self.assertTrue(
        passport_config, 'PassportHost not found in config for file {filename}.'
    )
    self.assertEqual(  # pylint: disable=g-generic-assert
        len(passport_config),
        1,
        'Expected exactly one PassportHost controller in config for file'
        f' {filename}.',
    )
    return peripheral_connector.PeripheralConnector(
        passport_host.PassportHost(passport_config[0])
    )

  @functools.with_variants(
      pasit_box_dock=(
          'pasit-box.yaml',
          peripheral_connector.ConnectionType.DOCK,
          peripheral_connector.ConnectionTag.DOCK,
          1,
      ),
      pasit_box_dockless=(
          'pasit-box.yaml',
          peripheral_connector.ConnectionType.DOCKLESS,
          peripheral_connector.ConnectionTag.DOCKLESS,
          1,
      ),
      pasit_box_daisy_chain=(
          'pasit-box.yaml',
          peripheral_connector.ConnectionType.DAISY_CHAIN,
          peripheral_connector.ConnectionTag.DAISY_CHAIN,
          1,
      ),
      pasit_box_dock_two_displays=(
          'pasit-box.yaml',
          peripheral_connector.ConnectionType.DOCK,
          peripheral_connector.ConnectionTag.DOCK,
          2,
      ),
      pasit_box_daisy_chain_two_displays=(
          'pasit-box.yaml',
          peripheral_connector.ConnectionType.DAISY_CHAIN,
          peripheral_connector.ConnectionTag.DAISY_CHAIN,
          2,
      ),
      non_standard_setup_dock=(
          'non-standard-setup.yaml',
          peripheral_connector.ConnectionType.DOCK,
          peripheral_connector.ConnectionTag.DOCK,
          1,
      ),
      non_standard_setup_dockless=(
          'non-standard-setup.yaml',
          peripheral_connector.ConnectionType.DOCKLESS,
          peripheral_connector.ConnectionTag.DOCKLESS,
          1,
      ),
      single_display_setup_dock=(
          'single-display.yaml',
          peripheral_connector.ConnectionType.DOCK,
          None,
          1,
      ),
  )
  def test_get_peripheral_path_tag(
      self,
      filename: str,
      connection_type: peripheral_connector.ConnectionType,
      expected_tag: peripheral_connector.ConnectionTag | None,
      min_display_count: int,
  ):
    connector = self._create_peripheral_connector(filename)
    path_tag = connector.get_peripheral_path_tag(
        pasit_host_pb2.PasitHost.Device.Type.MONITOR,
        connection_type,
        min_display_count,
    )
    self.assertEqual(path_tag, expected_tag)

  @functools.with_variants(
      pasit_box_dockless_two_displays=(
          'pasit-box.yaml',
          peripheral_connector.ConnectionType.DOCKLESS,
          2,
          peripheral_connector.PeripheralCountMismatchError,
          NOT_ENOUGH_PERIPHERALS_ERROR_REGEX,
      ),
      non_standard_setup_daisy_chain=(
          'non-standard-setup.yaml',
          peripheral_connector.ConnectionType.DAISY_CHAIN,
          1,
          peripheral_connector.PeripheralPathNotFoundError,
          NOT_FOUND_ERROR_REGEX,
      ),
      non_standard_setup_dock_two_displays=(
          'non-standard-setup.yaml',
          peripheral_connector.ConnectionType.DOCK,
          2,
          peripheral_connector.PeripheralCountMismatchError,
          NOT_ENOUGH_PERIPHERALS_ERROR_REGEX,
      ),
      non_standard_setup_dockless_two_displays=(
          'non-standard-setup.yaml',
          peripheral_connector.ConnectionType.DOCKLESS,
          2,
          peripheral_connector.PeripheralCountMismatchError,
          NOT_ENOUGH_PERIPHERALS_ERROR_REGEX,
      ),
      non_standard_setup_daisy_chain_two_displays=(
          'non-standard-setup.yaml',
          peripheral_connector.ConnectionType.DAISY_CHAIN,
          2,
          peripheral_connector.PeripheralPathNotFoundError,
          NOT_FOUND_ERROR_REGEX,
      ),
      single_display_setup_dockless=(
          'single-display.yaml',
          peripheral_connector.ConnectionType.DOCKLESS,
          1,
          peripheral_connector.PeripheralPathNotFoundError,
          NOT_FOUND_ERROR_REGEX,
      ),
      single_display_setup_daisy_chain=(
          'single-display.yaml',
          peripheral_connector.ConnectionType.DAISY_CHAIN,
          1,
          peripheral_connector.PeripheralPathNotFoundError,
          NOT_FOUND_ERROR_REGEX,
      ),
      single_display_setup_dock_two_displays=(
          'single-display.yaml',
          peripheral_connector.ConnectionType.DOCK,
          2,
          peripheral_connector.PeripheralCountMismatchError,
          NOT_ENOUGH_PERIPHERALS_ERROR_REGEX,
      ),
      single_display_setup_dockless_two_displays=(
          'single-display.yaml',
          peripheral_connector.ConnectionType.DOCKLESS,
          2,
          peripheral_connector.PeripheralPathNotFoundError,
          NOT_FOUND_ERROR_REGEX,
      ),
      single_display_setup_daisy_chain_two_displays=(
          'single-display.yaml',
          peripheral_connector.ConnectionType.DAISY_CHAIN,
          2,
          peripheral_connector.PeripheralPathNotFoundError,
          NOT_FOUND_ERROR_REGEX,
      ),
  )
  def test_get_peripheral_path_tag_raises_error(
      self,
      filename: str,
      connection_type: peripheral_connector.ConnectionType,
      min_display_count: int,
      exception_type: type[Exception],
      error_regex: str,
  ):
    connector = self._create_peripheral_connector(filename)
    with self.assertRaises(exception_type) as context:
      connector.get_peripheral_path_tag(
          pasit_host_pb2.PasitHost.Device.Type.MONITOR,
          connection_type,
          min_display_count,
      )
    self.assertRegex(str(context.exception), error_regex)


if __name__ == '__main__':
  unittest.main()
