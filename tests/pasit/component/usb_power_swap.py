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

from lib.pasit import pasit_test
from lib.pasit.passport import passport_usb_service_client as usb
from mobly import asserts
from mobly import test_runner


class UsbTesterHello(pasit_test.PasitTestClass):
  """A sample test demonstrating how to use the USB tester service."""

  def setup_class(self):
    super().setup_class()
    self.utc = self.passport_host.usb_tester_client

    # Open the USB tester with serial. TODO(danielgeorgem): move the serial to
    # the yaml file. so that the tester will be opened automatically by the
    # base class.
    testers = self.utc.get_usb_testers()
    logging.info("Found tester: %s", testers)

    # Check that the serial is in the list of testers.
    asserts.assert_true(
        "2409C109" in [i.id for i in testers.testers], "Serial not found."
    )
    self.utc.open_usb_tester("2409C109")

  def teardown_test(self):
    # The tester will be closed by the base class.
    self.passport_host.reset()

  def test_power_swap(self):
    roles_utc = [usb.PowerRole.SRC, usb.PowerRole.SNK] * 5
    roles_dut = ["SNK", "SRC"] * 5

    for utc_role, dut_role in zip(roles_utc, roles_dut):
      self.utc.power_role = utc_role
      time.sleep(10)
      ectool_output = self.dut.shell(["ectool", "typecstatus", "1"]).decode(
          "utf-8"
      )
      logging.info("ectool_output: %s", ectool_output)
      asserts.assert_true(
          f"Role:{dut_role}" in ectool_output,
          f"DUT did not switch to {dut_role}",
      )
      asserts.assert_true(
          self.utc.power_role == utc_role, f"UTC did not switch to {utc_role}"
      )


if __name__ == "__main__":
  test_runner.main()
