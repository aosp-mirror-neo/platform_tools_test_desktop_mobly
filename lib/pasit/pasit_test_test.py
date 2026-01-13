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

"""Unit tests for pasit_test.py."""

import unittest
from unittest import mock

from lib.pasit import pasit_test
from lib.pasit import pasit_test_config


class PasitTestTest(unittest.TestCase):
  """Unit tests for the PasitTestClass reboot behavior."""

  def setUp(self):
    super().setUp()
    self.pasit_test_instance = pasit_test.PasitTestClass(mock.MagicMock())
    self.pasit_test_instance.dut = mock.MagicMock()
    self.pasit_test_instance._test_failed = False

  def test_reboot_policy_none_on_success(self):
    self.pasit_test_instance.reboot_policy = pasit_test_config.RebootPolicy.NONE
    self.pasit_test_instance._handle_reboot_policy()
    self.pasit_test_instance.dut.safe_reset.assert_not_called()

  def test_reboot_policy_none_on_fail(self):
    self.pasit_test_instance._test_failed = True
    self.pasit_test_instance.reboot_policy = pasit_test_config.RebootPolicy.NONE
    self.pasit_test_instance._handle_reboot_policy()
    self.pasit_test_instance.dut.safe_reset.assert_not_called()

  def test_reboot_policy_on_fail_on_success(self):
    self.pasit_test_instance.reboot_policy = (
        pasit_test_config.RebootPolicy.ON_FAIL
    )
    self.pasit_test_instance._handle_reboot_policy()
    self.pasit_test_instance.dut.safe_reset.assert_not_called()

  def test_reboot_policy_on_fail_on_fail(self):
    self.pasit_test_instance._test_failed = True
    self.pasit_test_instance.reboot_policy = (
        pasit_test_config.RebootPolicy.ON_FAIL
    )
    self.pasit_test_instance._handle_reboot_policy()
    self.pasit_test_instance.dut.safe_reset.assert_called_once()

  def test_reboot_policy_on_teardown_on_success(self):
    self.pasit_test_instance.reboot_policy = (
        pasit_test_config.RebootPolicy.ON_TEARDOWN_TEST
    )
    self.pasit_test_instance._handle_reboot_policy()
    self.pasit_test_instance.dut.safe_reset.assert_called_once()

  def test_reboot_policy_on_teardown_on_fail(self):
    self.pasit_test_instance._test_failed = True
    self.pasit_test_instance.reboot_policy = (
        pasit_test_config.RebootPolicy.ON_TEARDOWN_TEST
    )
    self.pasit_test_instance._handle_reboot_policy()
    self.pasit_test_instance.dut.safe_reset.assert_called_once()


if __name__ == '__main__':
  unittest.main()
