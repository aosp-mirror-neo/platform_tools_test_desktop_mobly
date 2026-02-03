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
"""Mobly controller module for Human Motion Robot (HMR).

Controller methods are implemented to interact with the HMR touchhostD from:
https://chrome-internal.googlesource.com/chromeos/platform/human_motion_robot/+/refs/heads/main/touchhostd/


Sample Config:

.. code-block:: python

    "HmrDevice": [
        {
            "generation": "gen_2",
            "address": "192.168.1.123",
            "port": 5001
        }
    ]
"""

import enum
import logging
from typing import Any, cast, List
import xmlrpc.client

MOBLY_CONTROLLER_CONFIG_NAME = 'HmrDevice'

_HMR_PORT = 9992


class Error(Exception):
  """Error class for the HmrDevice controller."""


class HmrTestState(enum.StrEnum):
  """State of a GCode test job running on the HMRdevice."""

  NOT_STARTED = 'not_started'
  """A job has not yet been started nor run recently."""
  RUNNING = 'running'
  """A job is actively running."""
  COMPLETE = 'complete'
  """A job was recently completed."""
  UNKNOWN = 'unknown'
  """Job state is unknown."""

  @classmethod
  def from_str(cls, value: str):
    """Creates a HmrTestState enum member from a string value.

    Args:
      value: Output from HMR API /is_complete/ endpoint.
    Returns:
      A HmrTestState enum member.
    """
    match value:
      case 'NOT_STARTED':
        return cls.NOT_STARTED
      case 'RUNNING':
        return cls.RUNNING
      case 'COMPLETE':
        return cls.COMPLETE
      case _:
        return cls.UNKNOWN


class HmrDevice:
  """Represents a Human Motion Robot (HMR) device.

  Attributes:
    generation: The generation of the HMR device (e.g., 'gen_2').
    address: The IP address or hostname of the HMR device.
    port: The port number for communication with the HMR device.
    base_url: The base URL for communication with the HMR device.
  """

  def __init__(self, config: dict[str, Any]):
    self.generation = config['generation']
    if self.generation is None:
      raise Error('Missing required field "generation" in device configuration'
                  f' {config!r}.')
    self.address = config['address']
    if self.address is None:
      raise Error('Missing required field "address" in device configuration'
                  f' {config!r}.')
    self.port = config.get('port', _HMR_PORT)
    self.base_url = f'http://{self.address}:{self.port}'

  def get_info(self) -> dict[str, Any]:
    """Used to return info on controller."""
    return {
        'generation': self.generation,
        'address': self.address,
        'port': self.port
    }

  def test_connection(self) -> bool:
    """Used to check if device is accessible.

    Returns:
      True if connection doesn't fail, False otherwise.
    """
    try:
      with xmlrpc.client.ServerProxy(self.base_url) as proxy:
        proxy.TestConnection()
        return True
    except (xmlrpc.client.Fault, ConnectionRefusedError) as e:
      logging.error('TestConnection failed: %s', e)
      return False

  def get_all_files(self) -> List[Any]:
    """Return list of all files on HMR from default gcode directory.

    Returns:
      List of files in the default gcode directory on the HMR, may be empty.
      An empty list is also return if there are any errors.
    """
    try:
      with xmlrpc.client.ServerProxy(self.base_url) as proxy:
        response = proxy.GetAllFiles()
        return list(response)  # type: ignore
    except xmlrpc.client.Fault as e:
      logging.exception('Failed to retrieve file list on HMR: %s', e)
      return []

  def file_exists(self, file_name: str) -> bool:
    """Returns whether a file exists on the HMR.

    Args:
      file_name: Name/path of the file to check.

    Return:
      True if file exists, False otherwise.
    """
    with xmlrpc.client.ServerProxy(self.base_url) as proxy:
      response = bool(proxy.FileExists(file_name))
      return response
    return False

  def upload_file(self, file_name: str, file_data: bytes) -> bool:
    """Upload a file to the HMR.

    Args:
      file_name: Name/path of the file to upload
      file_data: Content of the file to upload

    Returns:
      True if file upload succeeded, False otherwise.
    """
    with xmlrpc.client.ServerProxy(self.base_url) as proxy:
      try:
        proxy.UploadFile(file_name, file_data)
      except xmlrpc.client.Fault as e:
        logging.exception('Failed to upload file \'%s\' to HMR: %s', file_name,
                          e)
        return False
    return True

  def delete_file(self, file_name: str) -> bool:
    """Delete a file from the HMR.

    Args:
      file_name: Name/path of the file to delete

    Returns:
      True if file exists, False otherwise.
    """
    with xmlrpc.client.ServerProxy(self.base_url) as proxy:
      try:
        proxy.DeleteFile(file_name)
      except xmlrpc.client.Fault as e:
        logging.exception('Failed to delete file \'%s\' on HMR: %s', file_name,
                          e)
        return False
    return True

  def start_job(self, file_name: str) -> None:
    """Start a HMR job for the given file name (Must be uploaded).

    Args:
      file_name: Name/path of the file to run
    """
    with xmlrpc.client.ServerProxy(self.base_url) as proxy:
      try:
        proxy.StartJob(file_name)
      except xmlrpc.client.Fault as e:
        logging.exception('Failed to start test job for file \'%s\' on HMR: %s',
                          file_name, e)

  def stop_job(self) -> None:
    """Stop currently running job on HMR."""
    try:
      with xmlrpc.client.ServerProxy(self.base_url) as proxy:
        proxy.StopJob()
    except (xmlrpc.client.Fault, ConnectionRefusedError) as e:
      logging.error('Failed to stop currently running job on HMR: %s', e)

  def create_directory(self, directory_path: str) -> None:
    """Create directory in HMR filesystem.

    Args:
      directory_path: Path of directory to create.
    """
    try:
      with xmlrpc.client.ServerProxy(self.base_url) as proxy:
        proxy.CreateDirectory(directory_path)
    except (xmlrpc.client.Fault, ConnectionRefusedError) as e:
      logging.error('Failed to create directory on HMR: %s', e)

  def get_progress(self) -> float:
    """Returns float corresponding to the progress of the current HMR job.

    1.0 = complete, 0.0 = hasn’t started.
    Gen_2 currently only reports 0.5 for "in progress", 0.0 otherwise.
    """
    try:
      with xmlrpc.client.ServerProxy(self.base_url) as proxy:
        response = proxy.GetProgress()
        return cast(float, response)
    except (xmlrpc.client.Fault, ConnectionRefusedError) as e:
      logging.error('Failed to get progress from HMR: %s', e)
      return 0.0

  def get_errors(self):
    """Get errors currently being reported by HMR.

    Not yet implemented in Gen2, implementing as placeholder.

    Returns:
      List of error codes currently emitted by HMR. If list is empty, no errors
      are being emitted.
    """
    pass

  def teardown(self):
    """Tears down the HMR device."""
    self.stop_job()


def create(configs: list[dict[str, Any]]) -> list['HmrDevice']:
  """Creates HMR device instances."""
  if not configs:
    raise Error(f'Missing configuration {configs!r}.')
  if len(configs) > 1:
    raise Error(f'Multiple HmrDevice configs are not supported: {configs!r}')
  return [HmrDevice(config) for config in configs]


def destroy(devices: list[HmrDevice]) -> None:
  """Closes all created HmrDevice instances."""
  for device in devices:
    try:
      device.teardown()
    except Exception:  # pylint: disable=broad-except
      logging.exception('Failed to clean up properly.')


def get_info(controllers: list[HmrDevice]) -> list[dict[str, Any]]:
  """Gets info from the controller objects used in a test run.

  Gets info from the controller objects used in a test
  run. The info will be included in test_summary.yaml under
  the key 'ControllerInfo'. Such information could include unique
  ID, version, or anything that could be useful for describing the
  test bed and debugging.

  Args:
    controllers: A list of controller objects created by the create function.

  Returns:
    A list of json serializable objects: each represents the
      info of a controller object. The order of the info
      object should follow that of the input objects.
  """
  return [controller.get_info() for controller in controllers]
