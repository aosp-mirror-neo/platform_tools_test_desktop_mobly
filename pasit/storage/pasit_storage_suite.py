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

"""PASIT Storage Suite."""

from mobly import base_suite
from mobly import config_parser
from mobly import suite_runner

from pasit.storage import eject_external_storage
from pasit.storage import write_to_external_storage


class PasitStorageSuite(base_suite.BaseSuite):
  """PASIT Storage Suite."""

  def setup_suite(self, config: config_parser.TestRunConfig):
    self.add_test_class(write_to_external_storage.WriteToExternalStorageTest)
    self.add_test_class(eject_external_storage.EjectExternalStorageTest)


def main() -> None:
  suite_runner.run_suite_class()

if __name__ == '__main__':
  main()
