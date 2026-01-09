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

"""AndroidPasitNetwork handles network status for PASIT testing on Android devices."""

import logging
import time

from lib.pasit.base import base_pasit_network
from lib.utils import retry
from mobly.controllers import android_device
from mobly.controllers.android_device_lib import adb


class AndroidPasitNetwork(base_pasit_network.BasePasitNetwork):
  """PasitNetwork implementation for Android devices."""

  def __init__(
      self,
      controller: android_device.AndroidDevice,
  ):
    super().__init__(controller)
    # ehide disables hides the servo/adb Ethernet port from Android so that
    # we can properly test other Ethernet devices, without ehide Android will
    # kill the secondary Ethernet connection since it already has an Ethernet
    # device with internet access.
    self._start_ehide()

  def cleanup(self):
    """Cleans up the network device.

    This should be called from the test flow when passport.reset() is called.
    """
    self._stop_ehide()

  def _start_ehide(self):
    self.controller.adb.shell(['start', 'ehide'])
    # need a short delay to ensure that ehide is started and the adb connection
    # glitch has happened before we wait for device and check if ehide is
    # running.
    time.sleep(1)
    self.controller.adb.wait_for_device(timeout=30)
    result = retry.retry(
        lambda: self.controller.adb.shell(['ehide-cli']),
        until=lambda result: 'stopped' not in result.decode(),
        policy=retry.RetryPolicy(max_tries=3, delay_seconds=2),
        exceptions=(adb.AdbError,),
    )
    if 'stopped' in result.decode():
      raise base_pasit_network.NetworkInfoError(
          'ehide failed to start, cannot test ethernet devices without ehide'
          ' running.'
      )

  def _stop_ehide(self):
    try:
      self.controller.adb.shell(['stop', 'ehide'])
    except adb.AdbError as e:
      # ignore error since adb will disconnect when ehide is stopped
      logging.debug('ehide failed to stop, ignoring error: %s', e)
    self.controller.adb.wait_for_device(timeout=30)

  def get_network_infos(self) -> dict[str, base_pasit_network.NetworkInfo]:
    # note this requires root which is already done in the test setup for
    # PASIT tests, but if that changes this will need to be updated.
    ip_link_json_str = self.controller.adb.shell(
        ['ip', '-json', 'link', 'show']
    )
    return self.ip_link_json_to_network_infos(ip_link_json_str.decode())

  def is_network_connected_to_internet(self, ifname: str) -> bool:
    try:
      # ping google.com 3 times with 30 seconds timeout
      result = self.controller.adb.shell(
          ['ping', '-c', '3', '-w', '30', '-q', '-I', ifname, 'google.com']
      )
      logging.debug(
          'is_network_connected_to_internet result: %s', result.decode()
      )
      return True
    except adb.AdbError as e:
      logging.debug(
          'Network %s is not connected to internet:\n\tstdout:'
          ' %s\n\tstderr: %s',
          ifname,
          e.stdout.decode(),
          e.stderr.decode(),
      )
      return False
