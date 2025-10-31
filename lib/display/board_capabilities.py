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

"""Define display capabilities and EDIDs for supported boards"""

from typing import Dict
from display.utils import edid_for_max_supported_modes
from mobly import asserts

EdidForMaxMode = edid_for_max_supported_modes.EdidForMaxMode

boardMaxSupportedRes: Dict[str, EdidForMaxMode] = {
    "fatcat": edid_for_max_supported_modes.edid_8k_60Hz_Timings,
    "brya": edid_for_max_supported_modes.edid_8k_60Hz_Timings,
}


def get_edid_for_max_supported_res_for_board(
    board_name: str,
) -> EdidForMaxMode | None:
  """Returns the EdidForMaxMode object for a given board name.

  Args:
      board_name: The name of the board (e.g., "fatcat", "brya").

  Returns:
      The EdidForMaxMode object or None if the board is not found.
  """
  edid_for_max_supported_mode_board = boardMaxSupportedRes.get(board_name)
  asserts.assert_not_equal(
      edid_for_max_supported_mode_board,
      None,
      f"Edid for Max supported mode for this board not found, please add this"
      f" to boardMaxSupportedRes",
  )
  return edid_for_max_supported_mode_board
