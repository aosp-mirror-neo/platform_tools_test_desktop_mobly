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

"""The module for PASIT display related imports and types."""

from mobly.controllers import android_device

from lib.pasit.android import android_pasit_display
from lib.pasit.base import base_pasit_display

PasitDisplay = base_pasit_display.BasePasitDisplay

# A dictionary of controller types and the corresponding PasitDisplay class.
# Used in PasitTestClass.create() to get the correct PasitDisplay class.
_registry = {
    android_device.AndroidDevice: android_pasit_display.AndroidPasitDisplay
}
