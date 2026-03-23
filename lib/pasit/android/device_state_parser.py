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

"""Parser for Device State and Form Factor output."""

import logging
import re
from lib.pasit.base import base_pasit_device
from mobly.controllers import android_device


FormFactor = base_pasit_device.FormFactor
DeviceState = base_pasit_device.DeviceState


class FormFactorParser:
  """Parser for device hardware form factor."""

  def __init__(self, controller: android_device.AndroidDevice):
    output = (
        controller.adb.shell(['dev_config', 'HardwareFeatures', 'form-factor'])
        .decode()
        .strip()
    )
    try:
      self.form_factor = FormFactor(output.upper())
    except ValueError:
      self.form_factor = FormFactor.UNKNOWN


class DeviceStateParser:
  """Parser for device state management.

  Translates ADB 'device_state' output into standardized Enums.
  """

  def __init__(self, controller: android_device.AndroidDevice):
    self.current_state = DeviceState.UNKNOWN

    states_raw = controller.adb.shell(
        ['cmd', 'device_state', 'print-states']
    ).decode()

    raw_id = controller.adb.shell(
        ['cmd', 'device_state', 'print-state']
    ).decode()
    match = re.search(r'(\d+)', raw_id)
    current_id = match.group(1) if match else raw_id.strip()

    self._parse_states(states_raw, current_id)

  def _parse_states(self, states_raw: str, current_id: str) -> None:
    """Parses raw shell output to populate state attributes.

    Args:
      states_raw: The raw output from 'cmd device_state print-states'.
      current_id: The raw numeric identifier from 'cmd device_state
        print-state'.
    """
    match = re.search(rf'identifier={current_id}, name=\'(\w+)\'', states_raw)
    if match:
      state_name = match.group(1).upper()
      try:
        self.current_state = DeviceState(state_name)
      except ValueError:
        logging.warning(
            "Current device state '%s' is not a known state in "
            'DeviceState enum.',
            state_name,
        )
