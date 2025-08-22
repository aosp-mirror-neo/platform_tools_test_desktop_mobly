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

"""UTC params class and generator for UTC-274 tests."""

from typing import Any

from lib.pasit.passport import passport_usb_service_client as usb


class UTCParams:
  """Class for passing UTC-274 params to testcases.

  This class defines the initial parameters for testcases.
  """

  def __init__(self, params: dict[str, Any]):
    # Attributes used for test name generation.
    self.port = params["port"]
    self.flip = params["flip"]
    self.name = params["name"]
    self.iterations = params.get("iterations", 1)

    # Attributes used for UTC-274 initialization.
    self.params = params

  def apply(self, utc: usb.PassportUsbServiceClient):
    """Applies the UTC params to the UTC-274."""
    utc.active_port = None
    utc.usb_channel = self.params["usb_channel"]
    utc.pd_init_state = self.params["pd_init_state"]
    utc.source_pdo_count = self.params["source_pdo_count"]
    utc.dpam_enabled = self.params["dpam_enabled"]

    # TODO(b/434628173) - Add cable flip once the bug is fixed.


def generate_utc_params(
    name: str,
    ports: list[int],
    flipped: bool = True,
    **overrides: dict[str, Any],
) -> list[UTCParams]:
  """Generates the UTC params for the UTC-274.

  Args:
    name: The name of the test, used for test name generation.
    ports: The list of ports to test.
    flipped: Whether to generate flipped cases.
    **overrides: Any additional overrides to the default params.

  Returns:
    A list of generated UTCParams objects.
  """
  params = []
  # TODO(b/434628173) - Add cable flip once the bug is fixed.
  flipped = False

  for port in ports:
    for flip in [True, False] if flipped else [False]:
      params.append(
          UTCParams(
              {
                  # Default params.
                  "port": port,
                  "flip": flip,
                  "name": name,
                  "active_cc": usb.ActiveCC.CC2 if flip else usb.ActiveCC.CC1,
                  "usb_channel": usb.UsbChannel.USB_3,
                  "pd_init_state": usb.InitPdState.PD_DRP,
                  "source_pdo_count": usb.DEFAULT_SRC_PDO_COUNT,
                  "dpam_enabled": False,
                  # Override params.
              }
              | overrides
          )
      )

  return params
