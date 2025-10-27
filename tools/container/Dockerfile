#  Copyright (C) 2024 The Android Open Source Project
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

# Build a Docker image for PASIT testbed suite.
#
# The container includes the built Mobly suite, and the APKs that are required
# to run the suite, along with the topology converter binary for converting
# the topologies to the format that is required by Mobly.
#
# To build the image, run:
# ./build_docker.sh
FROM debian:stable-slim
RUN apt update && apt install -y --no-install-recommends adb procps zip graphviz
RUN mkdir /workdir
COPY --from=suite DesktopPASITTestbedTests *.apk /tools/pasit/
COPY --from=host_bin topology_converter /tools/pasit/
WORKDIR /workdir
ENTRYPOINT ["/tools/pasit/DesktopPASITTestbedTests"]
