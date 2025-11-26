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

from lib.pasit import peripheral_connector
from lib.pasit.passport import passport_host
from lib.utils import functools
import yaml


NOT_FOUND_ERROR_REGEX = 'Display path .* not found in topology'
NOT_ENOUGH_DISPLAYS_ERROR_REGEX = (
    'Display count .* is less than minimum required count .*'
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
      dock=(
          peripheral_connector.ConnectionType.DOCK,
          peripheral_connector.ConnectionTag.DOCK,
      ),
      dockless=(
          peripheral_connector.ConnectionType.DOCKLESS,
          peripheral_connector.ConnectionTag.DOCKLESS,
      ),
      daisy_chain=(
          peripheral_connector.ConnectionType.DAISY_CHAIN,
          peripheral_connector.ConnectionTag.DAISY_CHAIN,
      ),
  )
  def test_setup_display_path_pasit_box(
      self,
      connection_type: peripheral_connector.ConnectionType,
      connection_tag: peripheral_connector.ConnectionTag,
  ):
    self._test_display_path('pasit-box.yaml', connection_type, connection_tag)

  @functools.with_variants(
      dock=(
          peripheral_connector.ConnectionType.DOCK,
          peripheral_connector.ConnectionTag.DOCK,
      ),
      dockless=(
          peripheral_connector.ConnectionType.DOCKLESS,
          peripheral_connector.ConnectionTag.DOCKLESS,
          NOT_ENOUGH_DISPLAYS_ERROR_REGEX,
      ),
      daisy_chain=(
          peripheral_connector.ConnectionType.DAISY_CHAIN,
          peripheral_connector.ConnectionTag.DAISY_CHAIN,
      ),
  )
  def test_setup_display_path_pasit_box_two_displays(
      self,
      connection_type: peripheral_connector.ConnectionType,
      connection_tag: peripheral_connector.ConnectionTag,
      error_regex: str | None = None,
  ):
    self._test_display_path(
        'pasit-box.yaml', connection_type, connection_tag, 2, error_regex
    )

  @functools.with_variants(
      dock=(
          peripheral_connector.ConnectionType.DOCK,
          peripheral_connector.ConnectionTag.DOCK,
      ),
      dockless=(
          peripheral_connector.ConnectionType.DOCKLESS,
          peripheral_connector.ConnectionTag.DOCKLESS,
      ),
      daisy_chain=(
          peripheral_connector.ConnectionType.DAISY_CHAIN,
          peripheral_connector.ConnectionTag.DAISY_CHAIN,
          NOT_FOUND_ERROR_REGEX,
      ),
  )
  def test_setup_display_path_non_standard_setup(
      self,
      connection_type: peripheral_connector.ConnectionType,
      connection_tag: peripheral_connector.ConnectionTag,
      error_regex: str | None = None,
  ):
    self._test_display_path(
        'non-standard-setup.yaml',
        connection_type,
        connection_tag,
        error_regex=error_regex,
    )

  # This non-standard setup has 2 displays, but only one is dockless and one is
  # dock so we expect a not enough displays error for all display paths.
  @functools.with_variants(
      dock=(
          peripheral_connector.ConnectionType.DOCK,
          peripheral_connector.ConnectionTag.DOCK,
          NOT_ENOUGH_DISPLAYS_ERROR_REGEX,
      ),
      dockless=(
          peripheral_connector.ConnectionType.DOCKLESS,
          peripheral_connector.ConnectionTag.DOCKLESS,
          NOT_ENOUGH_DISPLAYS_ERROR_REGEX,
      ),
      daisy_chain=(
          peripheral_connector.ConnectionType.DAISY_CHAIN,
          peripheral_connector.ConnectionTag.DAISY_CHAIN,
          NOT_FOUND_ERROR_REGEX,
      ),
  )
  def test_setup_display_path_non_standard_setup_two_displays(
      self,
      connection_type: peripheral_connector.ConnectionType,
      connection_tag: peripheral_connector.ConnectionTag,
      error_regex: str | None = None,
  ):
    self._test_display_path(
        'non-standard-setup.yaml',
        connection_type,
        connection_tag,
        2,
        error_regex,
    )

  @functools.with_variants(
      dock=(peripheral_connector.ConnectionType.DOCK,),
      dockless=(
          peripheral_connector.ConnectionType.DOCKLESS,
          NOT_FOUND_ERROR_REGEX,
      ),
      daisy_chain=(
          peripheral_connector.ConnectionType.DAISY_CHAIN,
          NOT_FOUND_ERROR_REGEX,
      ),
  )
  def test_setup_display_path_single_display_setup(
      self,
      connection_type: peripheral_connector.ConnectionType,
      error_regex: str | None = None,
  ):
    self._test_display_path(
        'single-display.yaml', connection_type, None, error_regex=error_regex
    )

  # This non-standard setup has 2 displays, but only one is dockless and one is
  # dock so we expect a not enough displays error for all display paths.
  @functools.with_variants(
      dock=(
          peripheral_connector.ConnectionType.DOCK,
          NOT_ENOUGH_DISPLAYS_ERROR_REGEX,
      ),
      dockless=(
          peripheral_connector.ConnectionType.DOCKLESS,
          NOT_FOUND_ERROR_REGEX,
      ),
      daisy_chain=(
          peripheral_connector.ConnectionType.DAISY_CHAIN,
          NOT_FOUND_ERROR_REGEX,
      ),
  )
  def test_setup_display_path_single_display_setup_two_displays(
      self,
      connection_type: peripheral_connector.ConnectionType,
      error_regex: str | None = None,
  ):
    self._test_display_path(
        'single-display.yaml', connection_type, None, 2, error_regex
    )

  def _test_display_path(
      self,
      filename: str,
      connection_type: peripheral_connector.ConnectionType,
      expected_display_path: peripheral_connector.ConnectionTag | None = None,
      min_display_count: int = 1,
      error_regex: str | None = None,
  ):
    connector = self._create_peripheral_connector(filename)
    try:
      display_path_tag = connector.get_display_path_tag(
          connection_type, min_display_count
      )
    except Exception as e:  # pylint: disable=broad-except
      logging.error('Error message: %s, error_regex: %s', e, error_regex)
      if error_regex:
        self.assertRegex(str(e), error_regex)  # pylint: disable=g-assert-in-except
        return
      else:
        raise
    self.assertEqual(display_path_tag, expected_display_path)
    self.assertNotEqual(error_regex, 'Expected error but no error was raised.')


if __name__ == '__main__':
  unittest.main()
