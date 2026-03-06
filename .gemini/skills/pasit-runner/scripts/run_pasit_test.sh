#!/bin/bash
#
# run_pasit_test.sh - A script to automate setting up and running PASIT Mobly tests.
#
# This script is part of the pasit-runner skill.
#
# Usage:
#   run_pasit_test.sh -d <DUT_NAME> -t <TEST_TARGET> [options]
#

set -e

# Default values
LEASE_MINUTES=120
ITERATIONS=1
PROVISION=""
SKIP_SETUP=false
TESTBED_NAME="pasit-android-testbed"

function usage() {
  echo "Usage: $0 -d <DUT_NAME> -t <TEST_TARGET> [options]"
  echo "  -d <DUT_NAME>    The hostname of the DUT."
  echo "  -t <TEST_TARGET> The atest target or path to test file."
  echo "  -p               Provision the DUT."
  echo "  -m <MINUTES>     Lease duration (default: 120)."
  echo "  -i <ITERATIONS>  Number of iterations."
  echo "  --skip-setup     Skip setup and tunnels step."
  exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -d) DUT_NAME="$2"; shift 2 ;;
    -t) TEST_TARGET="$2"; shift 2 ;;
    -p) PROVISION="-p"; shift ;;
    -m) LEASE_MINUTES="$2"; shift 2 ;;
    -i) ITERATIONS="$2"; shift 2 ;;
    --skip-setup) SKIP_SETUP=true; shift ;;
    *) usage ;;
  esac
done

if [[ -z "${DUT_NAME}" || -z "${TEST_TARGET}" ]]; then
  usage
fi

if [[ -z "${ANDROID_BUILD_TOP}" ]]; then
  echo "ERROR: ANDROID_BUILD_TOP is not set. Please run 'source build/envsetup.sh' and 'lunch' before running gemini."
  exit 1
fi

# Find project root (where tools/ exists)
PROJECT_ROOT="${ANDROID_BUILD_TOP}/tools/test/desktop/mobly"

if [[ ! -d "${PROJECT_ROOT}/tools/pasit" ]]; then
  echo "ERROR: Could not find tools/pasit directory from $ANDROID_BUILD_TOP"
  exit 1
fi

PASIT_SETUP_SCRIPT="${PROJECT_ROOT}/tools/pasit/pasit_setup_satlab.sh"
CONFIG_FILE="/tmp/mobly_config_${DUT_NAME}.yaml"

if crosfleet dut leases | grep -q "${DUT_NAME}"; then
  echo "DUT ${DUT_NAME} is  already leased."
  if [[ -f "${CONFIG_FILE}" ]]; then
    echo "Config file ${CONFIG_FILE} already exists."
    if grep -q "${DUT_NAME}" "${CONFIG_FILE}" & adb -s localhost:5555 shell getprop ro.build.fingerprint; then
      echo "DUT ${DUT_NAME} is already configured in ${CONFIG_FILE}."
      echo "Skipping setup and tunnels step."
      SKIP_SETUP=true
    fi
  fi
fi

if [[ "${SKIP_SETUP}" == false ]]; then
  # 1. Setup Satlab (Lease, Tunnels, Config)
  echo "Setting up Satlab and tunnels..."
  "${PASIT_SETUP_SCRIPT}" \
    -d "${DUT_NAME}" \
    -c "${CONFIG_FILE}" \
    -m "${LEASE_MINUTES}" \
    ${PROVISION}

  # Verify codename matches current lunch target if possible
  echo "Verifying DUT codename matches current lunch target..."
  CODENAME="$(get_build_var PLATFORM_VERSION_CODENAME || echo "")"
  DUT_CODENAME="$(adb -s localhost:5555 shell getprop ro.build.version.codename || echo "")"
  if [[ -n "${CODENAME}" && -n "${DUT_CODENAME}" && "${CODENAME}" != "${DUT_CODENAME}" && "${DUT_CODENAME}" != "REL" ]]; then
      echo "WARNING: DUT codename (${DUT_CODENAME}) does not match current target codename (${CODENAME})."
  fi
else
  echo "Skipping setup. Using existing config: ${CONFIG_FILE}"
  if [[ ! -f "${CONFIG_FILE}" ]]; then
    echo "ERROR: Config file ${CONFIG_FILE} not found."
    exit 1
  fi
fi

# 2. Verify ADB Connectivity
echo "Verifying ADB connectivity to localhost:5555..."
if ! adb -s localhost:5555 shell getprop ro.build.fingerprint > /dev/null 2>&1; then
    echo "Attempting to reconnect ADB..."
    adb connect localhost:5555
    sleep 2
fi

if ! adb -s localhost:5555 shell getprop ro.build.fingerprint; then
    echo "ERROR: Could not connect to DUT via ADB at localhost:5555."
    exit 1
fi

# 3. Run Test
echo "Running test: ${TEST_TARGET}"
ATEST_CMD=(atest -vtb "${TEST_TARGET}" -s localhost:5555)
if [[ "${ITERATIONS}" -gt 1 ]]; then
  ATEST_CMD+=(--iterations "${ITERATIONS}")
fi

# Add Mobly-specific args
ATEST_CMD+=(-- --testbed "${TESTBED_NAME}" --config "${CONFIG_FILE}")

echo "Executing: ${ATEST_CMD[*]}"
"${ATEST_CMD[@]}"
