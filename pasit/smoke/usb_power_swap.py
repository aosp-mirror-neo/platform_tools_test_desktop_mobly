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

"""A sample test demonstrating how to use the USB tester service."""

import logging
import time

from mobly import asserts
from mobly import test_runner

from pasit.lib import pasit_test
from pasit.lib.passport import passport_host


class UsbTesterHello(pasit_test.PasitTestClass):
  """A sample test demonstrating how to use the USB tester service."""

  def setup_class(self):
    super().setup_class()
    if self.passport_host.usb_tester_client is None:
      raise passport_host.PassportServiceConnectionError(
          'USB tester client is not initialized.'
      )

    # Open the USB tester with serial. TODO(danielgeorgem): move the serial to
    # the yaml file. so that the tester will be opened automatically by the
    # base class.
    testers = self.passport_host.usb_tester_client.get_usb_testers()
    logging.info('Found tester: %s', testers)

    # Check that the serial is in the list of testers.
    asserts.assert_true(
        '2409C109' in [i.id for i in testers.testers], 'Serial not found.'
    )
    self.passport_host.usb_tester_client.open_usb_tester('2409C109')

  def teardown_test(self):
    # The tester will be closed by the base class.
    self.passport_host.reset()

  def test_open_close_serial(self):
    if self.passport_host.usb_tester_client is None:
      raise passport_host.PassportServiceConnectionError(
          'USB tester client is not initialized.'
      )

    for _ in range(10):
      # The tester is the source so the DUT should be the sink.
      self.passport_host.usb_tester_client.set_power_role_to_src()
      time.sleep(10)
      ectool_output = self.dut.shell(['ectool', 'typecstatus', '1']).decode(
          'utf-8'
      )
      logging.info('ectool_output: %s', ectool_output)
      asserts.assert_true(
          'Role:SNK' in ectool_output, 'Role did not switch to SNK'
      )

      # The tester is the sink so the DUT should be the source.
      self.passport_host.usb_tester_client.set_power_role_to_snk()
      time.sleep(10)
      ectool_output = self.dut.shell(['ectool', 'typecstatus', '1']).decode(
          'utf-8'
      )
      logging.info('ectool_output: %s', ectool_output)
      asserts.assert_true(
          'Role:SRC' in ectool_output, 'Role did not switch to SRC'
      )


if __name__ == '__main__':
  test_runner.main()
