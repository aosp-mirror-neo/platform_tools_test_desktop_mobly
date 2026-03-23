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

"""Unit tests for device_state_parser."""

import unittest
from unittest import mock
from lib.pasit.android import device_state_parser
from lib.pasit.base import base_pasit_device


FULL_PRINT_STATES = """
Supported states: [
  DeviceState{identifier=0, name='CLOSED'},
  DeviceState{identifier=1, name='DOCKED'},
  DeviceState{identifier=2, name='OPEN'},
  DeviceState{identifier=3, name='TABLET'},
  DeviceState{identifier=99, name='EXPERIMENTAL_FOLD'},
]
"""


class DeviceStateParserTest(unittest.TestCase):
  """Unit tests for the DeviceStateParser class.

  Verifies that raw ADB shell output from 'cmd device_state' is correctly
  parsed into standardized Enums, handling both valid states and various
  malformed or unknown edge cases.
  """

  def _get_device_state_parser(
      self, states_out: str, current_id_out: str
  ) -> device_state_parser.DeviceStateParser:
    """Helper to create a parser with mocked ADB responses."""
    controller = mock.MagicMock()
    controller.adb.shell.side_effect = [
        states_out.encode('utf-8'),
        current_id_out.encode('utf-8'),
    ]
    return device_state_parser.DeviceStateParser(controller)

  def test_get_device_state_returns_correct_enum(self):
    """Tests parsing when the current ID maps perfectly to a known Enum."""
    parser = self._get_device_state_parser(FULL_PRINT_STATES, '3')
    self.assertEqual(parser.current_state, base_pasit_device.DeviceState.TABLET)

  def test_get_device_state_handles_case_insensitivity(self):
    """Verifies that the parser handles lowercase names in the shell output."""
    lowercase_mock = "DeviceState{identifier=2, name='open'}"
    parser = self._get_device_state_parser(lowercase_mock, '2')
    self.assertEqual(parser.current_state, base_pasit_device.DeviceState.OPEN)

  def test_get_device_state_defaults_to_unknown_on_errors(self):
    """Tests that structural failures default to UNKNOWN."""
    test_cases = [
        (FULL_PRINT_STATES, '5', 'ID not in map'),
        (FULL_PRINT_STATES, '', 'Empty current ID'),
        (FULL_PRINT_STATES, 'XYZ', 'Non-numeric current ID'),
        ('', '3', 'Empty print-states output'),
    ]

    for states_in, id_in, reason in test_cases:
      with self.subTest(reason=reason):
        parser = self._get_device_state_parser(states_in, id_in)
        self.assertEqual(
            parser.current_state, base_pasit_device.DeviceState.UNKNOWN
        )

  def test_get_device_state_logs_warning_for_unsupported_enum(self):
    """Verifies that a valid ID with an unknown Enum name logs a warning."""
    # ID 99 is 'EXPERIMENTAL_FOLD' in FULL_PRINT_STATES
    with self.assertLogs(level='WARNING') as cm:
      parser = self._get_device_state_parser(FULL_PRINT_STATES, '99')
      self.assertEqual(
          parser.current_state, base_pasit_device.DeviceState.UNKNOWN
      )
      log_output = ''.join(cm.output)
      self.assertIn('is not a known state in DeviceState enum', log_output)

  def test_form_factor_parsing_edge_cases(self):
    """Tests form factor parsing for both valid and invalid hardware strings."""
    test_cases = [
        (b'CONVERTIBLE', base_pasit_device.FormFactor.CONVERTIBLE),
        (b'detachable', base_pasit_device.FormFactor.DETACHABLE),
        (b'UNKNOWN_HARDWARE', base_pasit_device.FormFactor.UNKNOWN),
        (b'', base_pasit_device.FormFactor.UNKNOWN),
    ]

    for raw_output, expected_enum in test_cases:
      with self.subTest(raw_output=raw_output):
        controller = mock.MagicMock()
        controller.adb.shell.return_value = raw_output
        parser = device_state_parser.FormFactorParser(controller)
        self.assertEqual(parser.form_factor, expected_enum)


if __name__ == '__main__':
  unittest.main()
