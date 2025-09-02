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

"""AndroidDisplayId is a DisplayId for Android devices."""

import ctypes
from lib.pasit.base import base_pasit_display

DisplayId = base_pasit_display.BasePasitDisplay.DisplayId


class AndroidDisplayId(DisplayId):
  """AndroidDisplayId is a DisplayId for Android devices."""

  _unique_id: str

  def __new__(cls, display_id: str, unique_id: str):
    obj = DisplayId.__new__(cls, display_id)
    obj._unique_id = unique_id
    return obj

  @property
  def unique_id(self) -> str:
    return self._unique_id

  def __eq__(self, other):
    return self.id == other.id and self._unique_id == other._unique_id

  def __ne__(self, other):
    return self.id != other.id or self._unique_id != other._unique_id

  def __repr__(self):
    return f'{self.id}({self._unique_id})'

  def __hash__(self):
    return hash((self.id, self._unique_id))

  def unique_id_unsigned(self) -> str:
    """Returns the unique ID converted to from a signed to unsigned integer."""
    # TODO: b/442566979 - Remove this method once the bug is fixed. We can
    # likely just revert the entire CL that added this method when the bug is
    # fixed.
    id_int = int(self._unique_id)
    unsigned_id_int = ctypes.c_uint64(id_int).value
    return str(unsigned_id_int)

