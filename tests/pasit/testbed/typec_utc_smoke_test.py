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

"""A basic smoke test that validates communication with the USB Type-C (UTC) device."""

import logging
from lib.mobly.typec import utc_base_test
from mobly import asserts
from mobly import test_runner


class UtcSmokeTest(utc_base_test.UtcBaseTest):
  """Smoke tests to verify basic communication and functionality of the USB Type-C (UTC) device."""

  def test_utc_is_open(self):
    """Tests that the UTC can be opened."""
    asserts.assert_true(
        self.utc.is_open(),
        'UTC is not open, PASIT testbeds expect UTC to be open.',
    )

  def test_utc_dut_connectivity(self):
    """Tests that the UTC can be opened and VBUS can be sensed on each port."""
    asserts.assert_true(
        self.utc.is_open(),
        'UTC is not open, PASIT testbeds expect UTC to be open.',
    )

    for port in self.enabled_ports:
      logging.info('Enabling port %s', port)
      self.utc.active_port = port

      vbus_voltage = self.utc.vbus_voltage
      logging.info('Sensed VBUS voltage on port %s: %s', port, vbus_voltage)
      asserts.assert_true(
          vbus_voltage >= 0,
          f'Failed to sense valid VBUS voltage on port {port}',
      )

  # TODO(danielgeorgem): Re-enable this test once the Unigraf fixes the get
  # active_cc issue.
  # def test_electrical_cable_presence(self):
  #   """Tests that the UTC can change CC orientation on each port."""
  #   asserts.assert_true(
  #       self.utc.is_open(),
  #       'UTC is not open, PASIT testbeds expect UTC to be open.',
  #   )

  #   for port in self.enabled_ports:
  #     logging.info('Enabling port %s', port)
  #     self.utc.active_port = port

  #     logging.info('Setting orientation to CC2 on port %s', port)
  #     self.utc.active_cc = usb.ActiveCC.CC2
  #     asserts.assert_equal(
  #         self.utc.active_cc,
  #         usb.ActiveCC.CC2,
  #         f'Failed to set CC2 on port {port}',
  #     )

  #     logging.info('Setting orientation to CC1 on port %s', port)
  #     try:
  #       self.utc.active_cc = usb.ActiveCC.CC1
  #       asserts.assert_equal(
  #           self.utc.active_cc,
  #           usb.ActiveCC.CC1,
  #           f'Failed to set CC1 on port {port}',
  #       )
  #     except RuntimeError as e:
  #       logging.warning('Failed to set active_cc to CC1: %s', e)

  def test_pd_cap(self):
    """Tests that the UTC can enable and disable PD capability."""
    asserts.assert_true(
        self.utc.is_open(),
        'UTC is not open, PASIT testbeds expect UTC to be open.',
    )

    self.utc.pd_enabled = True
    asserts.assert_true(self.utc.pd_enabled, 'Failed to enable PD')

    self.utc.pd_enabled = False
    asserts.assert_false(self.utc.pd_enabled, 'Failed to disable PD')

    self.utc.pd_enabled = True

  def test_dp_cap(self):
    """Tests that the UTC can enable and disable DP capability."""
    asserts.assert_true(
        self.utc.is_open(),
        'UTC is not open, PASIT testbeds expect UTC to be open.',
    )

    self.utc.dpam_enabled = True
    asserts.assert_true(self.utc.dpam_enabled, 'Failed to enable DPAM')

    self.utc.dpam_enabled = False
    asserts.assert_false(self.utc.dpam_enabled, 'Failed to disable DPAM')

    self.utc.dpam_enabled = True

  def test_utc_caps_and_policies(self):
    """Tests reading power role, data role, usb channel, swap policies."""
    asserts.assert_true(
        self.utc.is_open(),
        'UTC is not open, PASIT testbeds expect UTC to be open.',
    )

    logging.info('Power role: %s', self.utc.power_role)
    logging.info('Data role: %s', self.utc.data_role)
    logging.info('USB channel: %s', self.utc.usb_channel)
    logging.info('Data swap policy: %s', self.utc.data_swap_policy)
    logging.info('Power swap policy: %s', self.utc.power_swap_policy)
    logging.info('VCONN swap policy: %s', self.utc.vconn_swap_policy)
    logging.info('PD enabled: %s', self.utc.pd_enabled)


if __name__ == '__main__':
  test_runner.main()
