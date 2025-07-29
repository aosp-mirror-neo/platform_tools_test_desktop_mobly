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

import logging

from typing import Optional, Dict
from enum import Enum
from display.utils import edid_for_max_supported_modes
from mobly import asserts
from lib.pasit import pasit_device

EdidForMaxMode = edid_for_max_supported_modes.EdidForMaxMode

# Define an Enum for the board names to ensure type safety and prevent typos.
class BoardName(Enum):
    FATCAT = "fatcat"
    BRYA = "brya"

# A map of board names to their corresponding EdidForMaxRes objects.
boardMaxSupportedRes: Dict[BoardName, EdidForMaxMode] = {
    BoardName.FATCAT: edid_for_max_supported_modes._8k_120Hz_Timings_EDID,
    BoardName.BRYA: edid_for_max_supported_modes._8k_60Hz_Timings_EDID
}

def get_current_board_name(dut: pasit_device.PasitDevice) -> str:
    """
    Executes the shell command 'adb shell getprop ro.product.device' and
    returns the output as the current board name.

    Returns:
        BoardName enum member or None: The current board name if the command is successful,
                    otherwise None.
    """
    try:
        ADB_SHELL_BOARD_NAME_CMD = "getprop ro.product.device"
        board_name_str = dut.shell(ADB_SHELL_BOARD_NAME_CMD.split()).decode("utf-8", errors="ignore").strip()
        logging.info("Current board under test model name is : %s", board_name_str)
        for name in BoardName:
            if name.value == board_name_str:
                return name
        assert False, "Add your board name to the BoardName Enum class and add its corresponding EDID"
        return None
    except Exception:
        return None

def get_edid_for_max_supported_res_for_board(board_name: BoardName) -> EdidForMaxMode:
    """
    Returns the EdidForMaxMode object for a given board name.

    Args:
        board_name: The name of the board (e.g., "fatcat", "brya").

    Returns:
        The EdidForMaxMode object or None if the board is not found.
    """
    edid_for_max_supported_mode_board = boardMaxSupportedRes.get(board_name)
    asserts.assert_not_equal(
        edid_for_max_supported_mode_board,
        None,
        f"Edid for Max supported mode for this board not found, please add this to boardMaxSupportedRes",
    )
    return edid_for_max_supported_mode_board
