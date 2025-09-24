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
"""Common errors and enums for PassportHost."""


class PassportBaseError(Exception):
  """Base error class for PassportHost."""


class DevicePathNotFoundError(PassportBaseError):
  """Error when trying to look up the path to a device."""


class PassportConfigError(PassportBaseError):
  """Error class for the PassportHost controller configuration."""


class PassportRPMError(PassportBaseError):
  """Error class for connecting to an RPM for a device via passport."""
