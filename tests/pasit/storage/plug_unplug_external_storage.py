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

"""Test external storage operability after plugging in and unplugging."""

from android.platform.test.annotations import DesktopTest
from lib.pasit import dut_state_manager
from lib.utils import functools
from mobly import test_runner
from pasit.storage import write_to_storage_base_test


@DesktopTest(
    cujs=[
        'b/379290617',  # Transfer and delete files
    ],
    manual=[
        'al_external_input.test_all_the_peripherals_connected_to_basic_usb_hub',
        'al_external_storage.boot_reboot_with_media_connected',
        'al_external_storage.plug_external_media_while_suspend',
        'al_external_storage.suspend_resume_with_media_connected',
        'al_external_storage.transfer_and_delete_files',
    ]
)
@functools.generate_tests
class PlugUnplugExternalStorageTest(
    write_to_storage_base_test.WriteToStorageBaseTest
):
  """Test external storage operability after plugging in and unplugging."""

  @functools.with_variants(
      on=(dut_state_manager.PowerState.ON,),
      off=(dut_state_manager.PowerState.OFF,),
      suspended=(dut_state_manager.PowerState.SUSPEND,),
  )
  def test_plug_in_storage_when_dut(
      self, state_when_plug_storage: dut_state_manager.PowerState
  ):
    """Test external storage operability after plugging in.

    Args:
      state_when_plug_storage: The power state of the DUT when external storage
        is plugged in.

    Write to external storage after plugging it in when DUT is in a specific
    state.
    """
    self.skip_if_servo_needed_and_not_configured(state_when_plug_storage)

    with dut_state_manager.EnterStateAndReturnToPowerOn(
        self.dut, state_when_plug_storage
    ):
      self.plug_in_external_storage()

    external_storage_path = self.verify_external_storage_mounted_or_reformat(
        'External storage not mounted after plugging in.'
    )
    external_storage_file_path = self.copy_file_to_external_storage(
        self.host_file_path, external_storage_path
    )
    self.verify_test_file_content_matches(
        external_storage_file_path, self.host_file_content
    )

  @functools.with_variants(
      on=(dut_state_manager.PowerState.ON,),
      suspended=(dut_state_manager.PowerState.SUSPEND,),
  )
  def test_unplug_storage_when_dut(
      self, state_when_unplug_storage: dut_state_manager.PowerState
  ):
    """Generate test logic for a specific dut state.

    Args:
      state_when_unplug_storage: The power state of the DUT when external
        storage is unplugged.

    Write to external storage after unplugging it when DUT is in a specific
    state and then replugging it.
    """
    self.skip_if_servo_needed_and_not_configured(state_when_unplug_storage)

    self.plug_in_external_storage()
    self.verify_external_storage_mounted_or_reformat(
        'External storage not mounted after plugging in.'
    )

    with dut_state_manager.EnterStateAndReturnToPowerOn(
        self.dut, state_when_unplug_storage
    ):
      self.unplug_external_storage()

    self.verify_external_storage_unmounted(
        'External storage not unmounted after unplugging.'
    )
    self.plug_in_external_storage()
    external_storage_path = self.verify_external_storage_mounted(
        'External storage not mounted after replugging.'
    )
    external_storage_file_path = self.copy_file_to_external_storage(
        self.host_file_path, external_storage_path
    )
    self.verify_test_file_content_matches(
        external_storage_file_path, self.host_file_content
    )


if __name__ == '__main__':
  test_runner.main()
