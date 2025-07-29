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

"""This module stores the EDID information for different displays."""

from dataclasses import dataclass, field
from display.utils import edid_datum
from display.utils import edids_list

EdidDatum = edid_datum.EdidDatum

@dataclass
class EdidForMaxMode:
    """
    Represents the EDID information for the maximum supported resolution of a display.
    """
    Hactive: int
    Vactive: int
    RefreshRate: int
    Edid: EdidDatum

    def __str__(self):
        """
        Provides a user-friendly string representation of the class instance.
        """
        return (f"Max Resolution EDID:\n"
                f"  Horizontal Active: {self.Hactive} pixels\n"
                f"  Vertical Active: {self.Vactive} pixels\n"
                f"  Refresh Rate: {self.RefreshRate} Hz\n"
                f"  EDID Data: {self.Edid.name if self.Edid else 'Not available'}")

_8k_120Hz_Timings_EDID = EdidForMaxMode(
    Hactive=7680,
    Vactive=4320,
    RefreshRate=120,
    # TODO Add the correct 8K120 EDID here b/441736353
    Edid=edids_list.UCD_500_DP1
)

_8k_60Hz_Timings_EDID = EdidForMaxMode(
   Hactive=7680,
    Vactive=4320,
    RefreshRate=60,
    # TODO Add the correct 8k60 EDID here b/441736353
    Edid=edids_list.UCD_500_DP1
)
