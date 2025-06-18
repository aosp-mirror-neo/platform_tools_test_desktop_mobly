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
"""IP 985x power controller."""

import http
import logging
import urllib.error
import urllib.parse
import urllib.request

from lib.pasit.passport import ip_power


class IP9850(ip_power.PassportRPM):
  """A class for controlling IP 9850 power switches for PASIT."""

  LOGIN_URL_STRING = 'set.cmd?user=admin+pass=12345678'

  def is_online(self) -> bool:
    """Returns True if the IP 9850 power switch is online.

    Checks if the IP 9850 power switch is reachable from the test host by
    attempting to retrieve the power status via HTTP.
    """
    address = f'{self.power_unit_endpoint}'
    url = f'http://{address}/{self.LOGIN_URL_STRING}+cmd=getpower'

    try:
      with urllib.request.urlopen(url, timeout=10) as response:
        resp_text = response.read()
        if response.status != http.HTTPStatus.OK:
          logging.debug(
              'IP 9850 online check failed for %s: %s',
              self.power_unit_endpoint,
              resp_text,
          )
          return False
        # If status is OK, assume online. Could add more robust checks if needed.
        return True
    except (
        urllib.error.URLError,
        http.client.BadStatusLine,
        ConnectionResetError,
    ) as e:
      logging.debug(
          'IP 9850 online check failed for %s: %s', self.power_unit_endpoint, e
      )
      return False

  def set_ip_power_state(self, power_state: ip_power.PowerState):
    """Sets the IP 9850 power state.

    Use the HTTP protocol to set the power state of the IP 9850 power switch.
    The IP 9850 power switch is controlled by sending an HTTP request to the
    frontend service.  This works with other AVIOSYS IP 985x products not just the
    9850.

    Args:
      power_state: The power state to set.

    Raises:
      PassportRPMError: If the HTTP request fails or returns an error.
    """
    address = f'{self.power_unit_endpoint}'
    set_string = f'p6{self.power_unit_outlet}={power_state.value}'
    url = f'http://{address}/{self.LOGIN_URL_STRING}+cmd=setpower+{set_string}'

    try:
      with urllib.request.urlopen(url, timeout=10) as response:
        resp_text = response.read()
        # Check status first, then content
        if response.status != http.HTTPStatus.OK:
          raise ip_power.PassportRPMError(
              f'Response status: {response.status}, response text: {resp_text}',
              self.power_unit_endpoint,
              power_state,
          )
        if set_string.encode('utf-8') not in resp_text:
          raise ip_power.PassportRPMError(
              f'Response OK ({response.status}) but expected string "{set_string}" not found in response text: {resp_text}',
              self.power_unit_endpoint,
              power_state,
          )
        logging.info(
            'Successfully set IP power state to %s for %s',
            power_state,
            self.power_unit_endpoint,
        )
    except (
        urllib.error.URLError,
        http.client.BadStatusLine,
        ConnectionResetError,
    ) as e:
      raise ip_power.PassportRPMError(
          f'URL request failed: {e}',
          self.power_unit_endpoint,
          power_state,
      ) from e
