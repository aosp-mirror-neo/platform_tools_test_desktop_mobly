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

"""Manages the lifecycle of the Passport container."""
import subprocess
import time

from lib.pasit.passport import errors


_PASSPORT_IMAGE = 'us-docker.pkg.dev/cros-passport/passport/passport:latest'


class PassportContainerManager:
  """Manages the lifecycle of the Passport container."""

  def __init__(self, logger):
    self.log = logger
    self._container_id = None

  def launch_container(self, config):
    """Launches the container if configured to do so.

    If the config parameter `container_orchestration` in the yaml file is set
    to True, the PassportHost controller will start the PassportAPI container
    on the host that is running the tests. For PassportAPI to function
    properly, any device controlled by passport should be connected directly
    to the host where PassportAPI is running.

    This method will modify the passed in config object to add the service
    host and port.

    Args:
      config: The configuration dictionary for the PassportHost.
    """
    if not config.get('container_orchestration', False):
      return

    command = [
        'docker',
        'run',
        '-d',
        '--privileged',
        '-v',
        '/dev/bus/usb:/dev/bus/usb',
        '-P',
        '--expose',
        '8300',
        _PASSPORT_IMAGE,
    ]

    try:
      self._container_id = (
          subprocess.check_output(command).decode('utf-8').strip()
      )
      self.log.info('Launched container with ID: %s', self._container_id)

      # Get the mapped port for container port 8300
      port_mapping_command = ['docker', 'port', self._container_id, '8300']
      port_mapping_output = (
          subprocess.check_output(port_mapping_command).decode('utf-8').strip()
      )
      # The output is in the format of 0.0.0.0:32768
      host_port = int(port_mapping_output.split(':')[-1])
      config['service_port'] = host_port
      config['service_host'] = 'localhost'
      self.log.info('Started passport on localhost:%d', host_port)

      # Wait for the service to start
      time.sleep(5)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
      self.log.error('Failed to launch docker container: %s', e)
      raise errors.PassportError('Failed to launch docker container') from e

  def teardown(self):
    """Tears down the container."""
    if self._container_id:
      self.log.info('Stopping and removing container %s', self._container_id)
      try:
        subprocess.run(
            ['docker', 'stop', self._container_id],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ['docker', 'rm', self._container_id],
            check=True,
            capture_output=True,
        )
        self._container_id = None
      except (subprocess.CalledProcessError, FileNotFoundError) as e:
        self.log.error(
            'Failed to stop/remove container %s: %s', self._container_id, e
        )
        if isinstance(e, subprocess.CalledProcessError):
          self.log.error('Stderr: %s', e.stderr.decode('utf-8'))

  # In case of unforseen exceptions, try to cleanup on delete
  def __del__(self):
    self.teardown()
