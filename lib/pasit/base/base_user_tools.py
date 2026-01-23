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

"""BaseUserTools provides a base class for user tools."""

import abc


class UserToolsError(Exception):
  """UserToolsError is raised when there is an error with a UserTools call."""


class BaseUserTools(abc.ABC):
  """Base class for user tools."""

  @abc.abstractmethod
  def skip_oobe(self) -> None:
    """Skips the OOBE flow."""
    raise NotImplementedError

  @abc.abstractmethod
  def login(self) -> None:
    """Logs in the user."""
    raise NotImplementedError

  @abc.abstractmethod
  def logout(self) -> None:
    """Logs out the user."""
    raise NotImplementedError
