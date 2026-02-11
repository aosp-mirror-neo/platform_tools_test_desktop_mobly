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

from chromiumos.test.lab.api.passport import video_tester_service_pb2
from display.utils import edid_for_max_supported_modes
from mobly import asserts

EdidForMaxMode = edid_for_max_supported_modes.EdidForMaxMode


class BoardDisplayCapabilities:
  """Stores the display capabilities of a board."""

  def __init__(
      self,
      edid_for_max_mode: EdidForMaxMode,
      dp_spec: video_tester_service_pb2.VideoSpecification,
      dsc: bool,
  ):
    self.edid_for_max_mode = edid_for_max_mode
    self.dp_spec = dp_spec
    self.dsc = dsc


board_display_capabilities: Dict[str, BoardDisplayCapabilities] = {
    'brya': BoardDisplayCapabilities(
        edid_for_max_mode=edid_for_max_supported_modes.edid_8k_30Hz_Timings,
        dp_spec=video_tester_service_pb2.VideoSpecification.VIDEO_SPECIFICATION_DP_1_4,
        dsc=True,
    ),
    'fatcat': BoardDisplayCapabilities(
        edid_for_max_mode=edid_for_max_supported_modes.edid_4k_160Hz_Timings,
        dp_spec=video_tester_service_pb2.VideoSpecification.VIDEO_SPECIFICATION_DP_2_1,
        dsc=False,
    ),
    'ruby': BoardDisplayCapabilities(
        edid_for_max_mode=edid_for_max_supported_modes.edid_4k_160Hz_Timings,
        dp_spec=video_tester_service_pb2.VideoSpecification.VIDEO_SPECIFICATION_DP_2_1,
        dsc=False,
    ),
    'lapis': BoardDisplayCapabilities(
        edid_for_max_mode=edid_for_max_supported_modes.edid_4k_160Hz_Timings,
        dp_spec=video_tester_service_pb2.VideoSpecification.VIDEO_SPECIFICATION_DP_2_1,
        dsc=False,
    ),
}


def get_board_display_capabilities(
    board_name: str,
) -> 'BoardDisplayCapabilities | None':
  """Returns the BoardDisplayCapabilities object for a given board name.

  Args:
    board_name: The name of the board (e.g., "fatcat", "brya").

  Returns:
    The BoardDisplayCapabilities object or None if the board is not found.
  """
  board_caps = board_display_capabilities.get(board_name)
  asserts.assert_not_equal(
      board_caps,
      None,
      'Display capabilities for this board not found, please add this to'
      ' board_display_capabilities',
  )
  return board_caps
