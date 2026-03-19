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

"""Helper class to get platform information."""

import logging
from lib.pasit import pasit_device
from mobly import asserts


def get_current_device_name(dut: pasit_device.PasitDevice) -> str | None:
  """Gets the device name (e.g., "redrix", "fatcat").

  Args:
      dut: The Pasit DUT.

  Returns:
      str or None: The current device name if the command is successful,
          otherwise None.
  """
  try:
    cmd = "getprop ro.product.device"
    device_name = (
        dut.shell(cmd.split()).decode("utf-8", errors="ignore").strip()
    )
    logging.debug("Current board under test device name is: %s", device_name)
    asserts.assert_true(
        device_name,
        "Could not get the current device name",
    )
    return device_name
  except RuntimeError:
    return None


def get_current_model_name(dut: pasit_device.PasitDevice) -> str | None:
  """Gets the board name (e.g., "redrix", "mithrax").

  Args:
      dut: The Pasit DUT.

  Returns:
      str or None: The current model name if the command is successful,
          otherwise None.
  """
  try:
    cmd = "getprop vendor.device.product.name"
    mode_name = dut.shell(cmd.split()).decode("utf-8", errors="ignore").strip()
    logging.info("Current board under test model name is: %s", mode_name)
    asserts.assert_true(
        mode_name,
        "Could not get the current model name",
    )
    return mode_name
  except RuntimeError:
    return None


# TODO(b/485856853): We can no longer query board, device is now the mode.
# Drop this from Compliance tests.
def get_current_board_model_names(
    dut: pasit_device.PasitDevice,
) -> tuple[str, str]:
  """Gets the board and model names (e.g., "brya", "redrix").

  Args:
      dut: The Pasit DUT.

  Returns:
      tuple[str, str]: A tuple containing the board and model names.
  """
  device_name = get_current_device_name(dut)
  model_name = get_current_model_name(dut)
  return device_name, model_name
