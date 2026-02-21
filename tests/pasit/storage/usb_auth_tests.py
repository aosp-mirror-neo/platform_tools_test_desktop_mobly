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

"""Test storage blocking behavior when the DUT is locked or on login screen."""

import logging

from android.platform.test.annotations import DesktopTest
from lib.pasit import dut_state_manager
from lib.pasit import peripheral_connector
from lib.utils import functools
from mobly import test_runner
from pasit.storage import storage_base_test


@DesktopTest(
    cujs=[
        'b/471033663',  # Verify new storage is blocked when the DUT is locked.
    ],
)
@functools.generate_tests
class USBAuthTests(storage_base_test.StorageBaseTest):
  """Verifies USB host authorization.

  Newly connected USB peripherals are not automatically
  trusted and require some form of explicit authorization
  before they can fully interact with the system.
  """

  @functools.with_variants(
      dock=(peripheral_connector.ConnectionType.DOCK,),
      dockless=(peripheral_connector.ConnectionType.DOCKLESS,),
  )
  def test_storage_blocked_on_lock_screen(
      self, connection_type: peripheral_connector.ConnectionType
  ):
    """Verifies that the storage is not mounted when the user locks the screen."""

    logging.info('Locking the DUT.')
    self.dut.user_tools.lock()

    self.plug_in_external_storage(connection_type=connection_type)

    self.verify_external_storage_unmounted(
        'External storage not unmounted when the user locks the DUT.'
    )
    logging.info('Storage access blocked while locked.')

    logging.info('Unlocking the DUT.')
    self.dut.user_tools.unlock()

    logging.info('Verifying storage mounts after unlock.')
    self.verify_external_storage_mounted(
        'Storage failed to mount after unlocking the device.'
    )

  @functools.with_variants(
      dock=(peripheral_connector.ConnectionType.DOCK,),
      dockless=(peripheral_connector.ConnectionType.DOCKLESS,),
  )
  def test_storage_blocked_until_login(
      self, connection_type: peripheral_connector.ConnectionType
  ):
    """Verifies that the storage is not mounted after power off until the user logs in."""

    self.skip_if_servo_needed_and_not_configured(
        dut_state_manager.PowerState.OFF
    )

    with dut_state_manager.EnterStateAndReturnToPowerOn(
        self.dut, dut_state_manager.PowerState.OFF,
        login_on_power_on=False
    ):
      self.plug_in_external_storage(connection_type=connection_type)

    self.verify_external_storage_unmounted(
        'External storage not unmounted when the DUT boots and before user'
        ' logs in.'
    )
    logging.info('Storage is blocked at login screen.')

    self.dut.user_tools.login()

    logging.info('Verifying storage mount after login.')
    self.verify_external_storage_mounted(
        'Storage failed to mount after logging in.'
    )


if __name__ == '__main__':
  test_runner.main()
