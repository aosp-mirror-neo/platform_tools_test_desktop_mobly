#!/bin/bash
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
# To build the image and push it to the container registry, run:
# ./build_docker.sh push [<tag: latest or staging>]

TAG="latest"

# last argument is the tag to apply to the image.
# If not specified, the default tag is "latest".
args=("$@")
last_arg="${args[-1]}"
if [[ -n "${last_arg}" ]] && [[ "${last_arg}" != "push" ]]; then
  TAG="${last_arg}"
fi

echo "Building Docker image with tag: ${TAG}..."

if ! m DesktopPASITTestbedTests topology_converter; then
  echo "Failed to build the suite and topology converter binaries."
  exit 1
fi

if ! docker build -t "us-docker.pkg.dev/cros-passport/testbed/android:${TAG}" \
  --build-context suite=${ANDROID_HOST_OUT_TESTCASES}/DesktopPASITTestbedTests/x86_64 \
  --build-context host_bin=${ANDROID_HOST_OUT}/bin \
  .; then
  echo "Failed to build the Docker image."
  exit 1
fi

if [[ "${1}" == "push" ]]; then
  docker push "us-docker.pkg.dev/cros-passport/testbed/android:${TAG}"
fi
