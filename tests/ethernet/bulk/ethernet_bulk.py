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

"""
Module test for the legion Ethernet pasit config, ie:
                 DUT
                  |
        USB programmable hub
                  |
        --------------------------
        |        |       |       |
    Dongle1  Dongle2  Dongle3 Dongle4  .....
        |--------|       |-------|
"""

import time
import logging
import sys

from lib.utils import retry
from lib.pasit.passport import passport_host
from mobly import asserts, base_test, test_runner
from mobly.controllers import android_device

from . import dongle


class DesktopInternalEthernetBulkTestCases(base_test.BaseTestClass):
    """Test suite for verifying Ethernet dongle enumeration and link state."""

    ENUMERATION_TIMEOUT = 10  # seconds
    LINK_UP_TIMEOUT = 15      # seconds
    POLL_INTERVAL = 1         # seconds

    def setup_class(self):
        """Initializes controllers and the rest of the dongle manager."""
        super().setup_class()
        # Register controllers
        self.ads = self.register_controller(android_device)
        self.dut = self.ads[0]
        self.passport = self.register_controller(passport_host)[0]

        # Finish initializing the dongle manager.
        self.dongle_manager.attach_dut(self.dut)
        self.dongle_manager.attach_passport(self.passport)

    def setup_test(self) -> None:
        """Ensures all dongles are powered off before each test case."""
        logging.info("Powering down all dongles for test setup.")
        self.dongle_manager.set_all_dongle_connect_state(
            dongle.EthDongle.ConnectionState.DISCONNECTED
        )
        # Allow a fixed time for all dongles to de-enumerate.
        time.sleep(self.ENUMERATION_TIMEOUT)

    def pre_run(self):
        """Dynamically generates tests for each discovered dongle."""
        # Create the dongle manager so that we can easily find the devices.
        self.dongle_manager = dongle.DongleManager(self.controller_configs)

        # Use dongle object as the unique parameter
        params = [(d,) for d in self.dongle_manager.dongles]

        self.generate_tests(
            test_logic=self._test_enumeration,
            name_func=lambda d: f"test_enumeration_{d.model.replace(' ', '_')}",
            arg_sets=params,
        )

        self.generate_tests(
            test_logic=self._test_link_up,
            name_func=lambda d: f"test_link_up_{d.model.replace(' ', '_')}",
            arg_sets=params,
        )

    def _test_enumeration(self, dongle_obj: dongle.EthDongle):
        """Verifies a dongle can be enumerated and de-enumerated."""
        # Dongles are powered off in setup_test, confirm it's absent.
        self.wait_for_enumeration(
            dongle_obj, dongle.EthDongle.EnumerationState.ABSENT
        )

        # Power on the dongle and ensure it appears.
        logging.info("Powering on dongle %s to test enumeration.", dongle_obj)
        self.dongle_manager.set_dongle_connect_state(
            dongle_obj, dongle.EthDongle.ConnectionState.CONNECTED
        )
        self.wait_for_enumeration(
            dongle_obj, dongle.EthDongle.EnumerationState.ENUMERATED
        )

    def _test_link_up(self, dongle_obj: dongle.EthDongle):
        """Verifies a dongle and its partner can establish a link."""
        partner = dongle_obj.partner
        asserts.assert_is_not_none(
            partner, f"Dongle {dongle_obj.mac} has no partner to test link."
        )
        logging.info("Testing link-up between %s and partner %s", dongle_obj, partner)

        # Confirm both are absent from setup_test.
        self.wait_for_enumeration(dongle_obj, dongle.EthDongle.EnumerationState.ABSENT)
        self.wait_for_enumeration(partner, dongle.EthDongle.EnumerationState.ABSENT)

        # Power on the dongle and its partner.
        logging.info("Powering on both dongles to test link state.")
        self.dongle_manager.set_dongle_connect_state(
            dongle_obj, dongle.EthDongle.ConnectionState.CONNECTED
        )
        self.dongle_manager.set_dongle_connect_state(
            partner, dongle.EthDongle.ConnectionState.CONNECTED
        )

        # Verify both are enumerated.
        self.wait_for_enumeration(dongle_obj, dongle.EthDongle.EnumerationState.ENUMERATED)
        self.wait_for_enumeration(partner, dongle.EthDongle.EnumerationState.ENUMERATED)

        # Verify both have an active link.
        self.wait_for_connection_state(dongle_obj, dongle.EthDongle.ConnectionState.CONNECTED)
        self.wait_for_connection_state(partner, dongle.EthDongle.ConnectionState.CONNECTED)

    def wait_for_enumeration(
        self, dongle_obj: dongle.EthDongle, expected_state: dongle.EthDongle.EnumerationState
    ):
        """Waits for a dongle to reach the expected enumeration state."""
        final_state = retry.retry(
            func=lambda: dongle_obj.enumeration_state,
            until=lambda state: state == expected_state,
            max_tries=self.ENUMERATION_TIMEOUT // self.POLL_INTERVAL,
            delay_seconds=self.POLL_INTERVAL,
        )

        if final_state != expected_state:
            raise TimeoutError(
                f"Dongle {dongle_obj.mac} did not reach enumeration state "
                f"'{expected_state.name}' within {self.ENUMERATION_TIMEOUT}s."
            )

    def wait_for_connection_state(
        self, dongle_obj: dongle.EthDongle, expected_state: dongle.EthDongle.ConnectionState
    ):
        """Waits for a dongle's interface to reach the expected connection state."""
        final_state = retry.retry(
            func=lambda: dongle_obj.connection_state,
            until=lambda state: state == expected_state,
            max_tries=self.LINK_UP_TIMEOUT // self.POLL_INTERVAL,
            delay_seconds=self.POLL_INTERVAL,
            exceptions=(dongle.InterfaceNotFoundError,),
        )

        if final_state != expected_state:
            raise TimeoutError(
                f"Dongle {dongle_obj.mac} interface did not reach connection state "
                f"'{expected_state.name}' within {self.LINK_UP_TIMEOUT}s."
            )


if __name__ == '__main__':
  if '--' in sys.argv:
    index = sys.argv.index('--')
    sys.argv = sys.argv[:1] + sys.argv[index + 1 :]
  test_runner.main()
