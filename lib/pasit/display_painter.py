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

"""The module for PASIT display painter related imports and types."""

from lib.pasit.android import android_display_painter
from lib.pasit.base import base_display_painter
from mobly.controllers import android_device


DisplayPainter = base_display_painter.BaseDisplayPainter

# A dictionary of controller types and the corresponding DisplayPainter class.
# Used in PasitTestClass.create() to get the correct DisplayPainter class.
registry = {
    android_device.AndroidDevice: android_display_painter.AndroidDisplayPainter
}
