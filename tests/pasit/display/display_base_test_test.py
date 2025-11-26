import logging
import os
import sys
import unittest
from unittest import mock

import display_base_test
from lib.pasit.passport import passport_host
from lib.utils import functools
from mobly import signals
import yaml


NOT_FOUND_ERROR_REGEX = 'Display path .* not found in topology'
NOT_ENOUGH_DISPLAYS_ERROR_REGEX = (
    'Display count .* is less than minimum required count .*'
)


@functools.generate_tests
class DisplayBaseTestTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    # Setup logging to stdout so we can see the logs in the test results.
    # Note it must be to stdout and not stderr, otherwise the logs interfere
    # with the parsing of the test results.
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    self.data_dir = os.path.join(
        # due to the way files are packaged in the par file/build dir, we need
        # to walk up the directory tree twice to get to the right spot.
        os.path.dirname(os.path.dirname(display_base_test.__file__)),
        'data',
    )
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

  def _create_test_instance(self, filename):
    """Creates an instance of DisplayBaseTest with a mocked passport_host."""
    with open(os.path.join(self.data_dir, filename), 'r') as f:
      config = yaml.safe_load(f)
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
    test_instance = display_base_test.DisplayBaseTest.__new__(
        display_base_test.DisplayBaseTest
    )
    test_instance.passport_host = passport_host.PassportHost(passport_config[0])
    return test_instance

  @functools.with_variants(
      dock=(
          display_base_test.ConnectionType.DOCK,
          display_base_test.ConnectionTag.DOCK,
      ),
      dockless=(
          display_base_test.ConnectionType.DOCKLESS,
          display_base_test.ConnectionTag.DOCKLESS,
      ),
      daisy_chain=(
          display_base_test.ConnectionType.DAISY_CHAIN,
          display_base_test.ConnectionTag.DAISY_CHAIN,
      ),
  )
  def test_setup_display_path_pasit_box(
      self,
      connection_type: display_base_test.ConnectionType,
      connection_tag: display_base_test.ConnectionTag,
  ):
    self._test_display_path('pasit-box.yaml', connection_type, connection_tag)

  @functools.with_variants(
      dock=(
          display_base_test.ConnectionType.DOCK,
          display_base_test.ConnectionTag.DOCK,
      ),
      dockless=(
          display_base_test.ConnectionType.DOCKLESS,
          display_base_test.ConnectionTag.DOCKLESS,
          NOT_ENOUGH_DISPLAYS_ERROR_REGEX,
      ),
      daisy_chain=(
          display_base_test.ConnectionType.DAISY_CHAIN,
          display_base_test.ConnectionTag.DAISY_CHAIN,
      ),
  )
  def test_setup_display_path_pasit_box_two_displays(
      self,
      connection_type: display_base_test.ConnectionType,
      connection_tag: display_base_test.ConnectionTag,
      error_regex: str | None = None,
  ):
    self._test_display_path(
        'pasit-box.yaml', connection_type, connection_tag, 2, error_regex
    )

  @functools.with_variants(
      dock=(
          display_base_test.ConnectionType.DOCK,
          display_base_test.ConnectionTag.DOCK,
      ),
      dockless=(
          display_base_test.ConnectionType.DOCKLESS,
          display_base_test.ConnectionTag.DOCKLESS,
      ),
      daisy_chain=(
          display_base_test.ConnectionType.DAISY_CHAIN,
          display_base_test.ConnectionTag.DAISY_CHAIN,
          NOT_FOUND_ERROR_REGEX,
      ),
  )
  def test_setup_display_path_non_standard_setup(
      self,
      connection_type: display_base_test.ConnectionType,
      connection_tag: display_base_test.ConnectionTag,
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
          display_base_test.ConnectionType.DOCK,
          display_base_test.ConnectionTag.DOCK,
          NOT_ENOUGH_DISPLAYS_ERROR_REGEX,
      ),
      dockless=(
          display_base_test.ConnectionType.DOCKLESS,
          display_base_test.ConnectionTag.DOCKLESS,
          NOT_ENOUGH_DISPLAYS_ERROR_REGEX,
      ),
      daisy_chain=(
          display_base_test.ConnectionType.DAISY_CHAIN,
          display_base_test.ConnectionTag.DAISY_CHAIN,
          NOT_FOUND_ERROR_REGEX,
      ),
  )
  def test_setup_display_path_non_standard_setup_two_displays(
      self,
      connection_type: display_base_test.ConnectionType,
      connection_tag: display_base_test.ConnectionTag,
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
      dock=(display_base_test.ConnectionType.DOCK,),
      dockless=(
          display_base_test.ConnectionType.DOCKLESS,
          NOT_FOUND_ERROR_REGEX,
      ),
      daisy_chain=(
          display_base_test.ConnectionType.DAISY_CHAIN,
          NOT_FOUND_ERROR_REGEX,
      ),
  )
  def test_setup_display_path_single_display_setup(
      self,
      connection_type: display_base_test.ConnectionType,
      error_regex: str | None = None,
  ):
    self._test_display_path(
        'single-display.yaml', connection_type, None, error_regex=error_regex
    )

  # This non-standard setup has 2 displays, but only one is dockless and one is
  # dock so we expect a not enough displays error for all display paths.
  @functools.with_variants(
      dock=(
          display_base_test.ConnectionType.DOCK,
          NOT_ENOUGH_DISPLAYS_ERROR_REGEX,
      ),
      dockless=(
          display_base_test.ConnectionType.DOCKLESS,
          NOT_FOUND_ERROR_REGEX,
      ),
      daisy_chain=(
          display_base_test.ConnectionType.DAISY_CHAIN,
          NOT_FOUND_ERROR_REGEX,
      ),
  )
  def test_setup_display_path_single_display_setup_two_displays(
      self,
      connection_type: display_base_test.ConnectionType,
      error_regex: str | None = None,
  ):
    self._test_display_path(
        'single-display.yaml', connection_type, None, 2, error_regex
    )

  def _test_display_path(
      self,
      filename: str,
      connection_type: display_base_test.ConnectionType,
      expected_display_path: display_base_test.ConnectionTag | None = None,
      min_display_count: int = 1,
      error_regex: str | None = None,
  ):
    test = self._create_test_instance(filename)
    try:
      test.setup_display_path(connection_type, min_display_count)
    except signals.TestSkip as e:
      logging.error('Error message: %s, error_regex: %s', e, error_regex)
      if error_regex:
        self.assertRegex(str(e), error_regex)
        return
      else:
        raise
    self.assertEqual(test.display_path_tag, expected_display_path)
    self.assertNotEqual(error_regex, 'Expected error but no error was raised.')


if __name__ == '__main__':
  unittest.main()
