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

"""A module for building and representing EDID configurations."""

from display.utils import interface_types


class EdidDatum:
  """Represents an EDID configuration for a display."""

  name: str
  interface_type: interface_types.InterfaceType
  edid_hex_string: str
  is_4k: bool
  is_hdr: bool
  is_vrr: bool

  def __init__(
      self,
      interface_type: interface_types.InterfaceType,
      edid_hex_string: str,
      is_4k: bool = False,
      is_hdr: bool = False,
      is_vrr: bool = False,
  ):
    """Initializes an Edid instance.

    Args:
      interface_type: The display interface type (DP or HDMI).
      edid_hex_string: The EDID data as a hexadecimal string.
      is_4k: Whether the EDID is for a 4K display.
      is_hdr: Whether the EDID is for a HDR display.
      is_vrr: Whether the EDID is for a VRR display.
    """
    self.interface_type = interface_type
    self.edid_hex_string = edid_hex_string
    self.is_4k = is_4k
    self.is_hdr = is_hdr
    self.is_vrr = is_vrr

  def to_bytes(self) -> bytes:
    """Converts the EDID hex string to a bytes object.

    Removes whitespace before conversion.

    Returns:
      The EDID data as bytes.

    Raises:
      ValueError: If the hex string is invalid.
    """
    # Clean up whitespace or newlines from the hex string
    clean_hex = ''.join(self.edid_hex_string.split())
    return bytes.fromhex(clean_hex)

  def __str__(self) -> str:
    """Provides a user-friendly representation."""
    return f'{self.name} ({self.interface_type.value})'

