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

"""Test that counts the number of displays on the DUT."""


from pasit.display import display_base_test


class DisplayCountTest(display_base_test.DisplayBaseTest):
  """Test that counts the number of displays on the DUT."""

  def test_display_count(self):
    """Test that counts the number of displays on the DUT."""
    self._verify_display_count(1, 'before external display plug in')
    self._capture_display_images('before_plug_in')

    self._plug_in_external_display()
    self._verify_display_count(2, 'after external display plug in')
    self._capture_display_images('after_plug_in')

    self._unplug_external_display()
    self._verify_display_count(1, 'after external display unplug')
