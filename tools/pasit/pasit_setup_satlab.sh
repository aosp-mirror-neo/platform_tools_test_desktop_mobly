#!/bin/bash
#
# This script is used to run pasit tests from a workstation remotely on Satlab
# DUTs, more info: go/pasit-satlab-tast
#
# For usage info run:
#   pasit_setup_satlab.sh -h
#
# The script will setup the following tunnels:
#   - 5555:DUT_HOSTNAME:5555 (DUT ADB)
#   - 8300:172.17.0.4:8300 (Passport)
#   - 8080:192.168.231.110:80 (IP Power Switch)
#   - 9999:SERVO_IP:9999 (Servod)
#
#
# roughly this script does the following:
# 1. Determine the DUT/Servo parameters
# 2. start servod container on the Satlab
# 3. start passport container on the Satlab
# 4. setup a tunnel to the DUT, Servod/Passport containers, and the pasit
#    IP power switch
#
# once that is done the user can run mobly tests locally from their workstation
#
# Dependencies:
#   - shivas command installed on PATH go/shivas
#   - crosfleet command installed on PATH go/crosfleet-cli
#   - jq command installed (`sudo apt install jq`)


# default tunnel ports
DUT_ADB_TUNNEL_PORT=5555
PASSPORT_TUNNEL_PORT=8300
DUT_SSH_TUNNEL_PORT=2200
IP_POWER_SWITCH_TUNNEL_PORT=8080
SERVOD_TUNNEL_PORT=9999

# constants
DUT_LEASE_MINUTES=120
SERVOD_PORT=9999
IP_POWER_SWITCH_IP="192.168.231.110"
PASSPORT_DOCKER_REGISTRY="us-docker.pkg.dev/cros-passport"
PASSPORT_DOCKER_IMAGE="${PASSPORT_DOCKER_REGISTRY}/passport/passport:latest"
PASSPORT_CONTAINER="passport-dev"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

function usage() {
  echo "Usage: pasit_setup_satlab.sh -d <DUT_HOSTNAME> -s <SATLAB_IP> [-p]"
  echo "  -d|--dut_hostname: The hostname of the DUT to use for testing."
  echo "  -s|--satlab_ip: The IP of the Satlab to use for testing."
  echo "  -p|--provision: Provision the DUT before leasing (will only run if"
  echo "                  the DUT is not already leased)."
  echo "  -m|--minutes: The number of minutes to lease the DUT for."
  echo "  -c|--config-generate: Generate the config yaml file for the DUT using"
  echo "                  data from shivas pasit topology."
  echo "  --skip-lease: Skip leasing the DUT."
  echo "  --skip-servo-setup: Skip setting up servod container."
  echo "  --port-offset: An integer to offset all the tunnel ports by."
  echo "  --cros: Run the script to test CrOS devices (default is Android)."
  echo ""
  echo "Example:"
  echo "  pasit_setup_satlab.sh -d <DUT_HOSTNAME> -s <SATLAB_IP> [-c /path/to/config.yaml]"
  echo ""
  echo "For more instructions see go/write-pasit-test."
  exit 1
}

function check_ssh_access() {
  echo -e "\n\nChecking SSH access to ${SATLAB_IP}..."
  if ! ssh -o BatchMode=yes "${SATLAB_IP}" "echo 'SSH access successful.'" > /dev/null 2>&1; then
    echo -e "\n\nERROR: Failed to establish SSH connection to ${SATLAB_IP}."
    echo "Please ensure you have passwordless SSH access configured for this Satlab and that the host key is accepted."
    echo "See go/write-pasit-test#enter-satlab-dut for more details."
    exit 1
  fi
  echo "SSH access to ${SATLAB_IP} successful."
}

function check_dependencies() {
  echo -e "\n\nChecking script dependencies..."

  # Check for always required tools
  if ! which adb > /dev/null 2>&1; then
    echo "ERROR: adb command not found. Please ensure adb is installed or you are running from Android build dir that has adb."
    exit 1
  fi

  # Check for tools needed for crosfleet/shivas/provisioning steps
  if [[ "${SKIP_LEASE}" != true || "${SKIP_SETUP_SERVO}" != true || "${PROVISION}" == true ]]; then
    if ! which jq > /dev/null 2>&1; then
      echo "ERROR: jq command not found. Please install jq (e.g., sudo apt install jq)."
      exit 1
    fi

    if ! which shivas > /dev/null 2>&1; then
      echo "ERROR: shivas command not found. Please ensure shivas is installed and on your PATH."
      echo "See go/shivas for installation instructions."
      exit 1
    fi

    if ! which crosfleet > /dev/null 2>&1; then
      echo "ERROR: crosfleet command not found. Please ensure crosfleet is installed and on your PATH."
      echo "See go/crosfleet-cli for installation instructions."
      exit 1
    fi
  fi
  echo "All required dependencies found."
}

function run_command_on_satlab_ignore_error() {
  # runs command on satlab in a bash shell so that we get env vars
  # and path as if we were running command from interactive shell
  # this assumes that no variable expanision is needed on the remote
  # ssh shell
  ssh "${SATLAB_IP}" -t "bash -l -c '$*'"
}

function run_command_on_satlab() {
  # runs command on satlab in a bash shell so that we get env vars
  # and path as if we were running command from interactive shell
  # this assumes that no variable expanision is needed on the remote
  # ssh shell
  run_command_on_satlab_ignore_error $@
  if [[ $? -ne 0 ]]; then
    echo -e "\n\nERROR: Failed to run command on Satlab ${SATLAB_IP}: $*"
    exit 1
  fi
}

function setup_tunnel() {
  TUNNEL_PGREP="ssh -fNT -L.*${DUT_ADB_TUNNEL_PORT}"
  if [[ "${CROS_TESTING}" == true ]]; then
    TUNNEL_PGREP="ssh -fNT -L.*${DUT_SSH_TUNNEL_PORT}"
  fi
  echo "Killing existing tunnels to ${TUNNEL_PGREP}..."
  pgrep -f "${TUNNEL_PGREP}" | xargs kill -9 > /dev/null 2>&1
  # background tunnel to the DUT
  if [[ ! -z "${SERVO_IP}" ]]; then
    SERVO_TUNNEL="-L ${SERVOD_TUNNEL_PORT}:${SERVO_IP}:${SERVOD_PORT}"
  fi

  local DUT_TUNNEL
  if [[ "${CROS_TESTING}" == true ]]; then
    DUT_TUNNEL="-L ${DUT_SSH_TUNNEL_PORT}:${DUT_HOSTNAME}:22"
  else
    DUT_TUNNEL="-L ${DUT_ADB_TUNNEL_PORT}:${DUT_HOSTNAME}:5555"
  fi

  # shellcheck disable=SC2086
  ssh -fNT \
    "${DUT_TUNNEL}" \
    -L "${PASSPORT_TUNNEL_PORT}:${PASSPORT_IP}:8300" \
    -L "${IP_POWER_SWITCH_TUNNEL_PORT}:${IP_POWER_SWITCH_IP}:80" \
    ${SERVO_TUNNEL} \
    "${SATLAB_IP}"
  if [[ $? -ne 0 ]]; then
    echo -e "\n\nERROR: Failed to start SSH tunnel to ${SATLAB_IP}"
    exit 1
  fi
  echo "SSH tunnel to ${DUT_HOSTNAME} started"
}

function start_passport() {
  echo -e "\n\nStarting passport container..."
  # don't use the run_command_on_satlab function in this function because
  # there is too much quoting going on and it will mess up the command parsing
  local DOCKER_CMD="$(ssh "${SATLAB_IP}" which docker)"
  if [[ -z "${DOCKER_CMD}" ]]; then
    DOCKER_CMD="/usr/local/bin/docker"
    echo -e "defaulting to satlab docker path ${DOCKER_CMD}"
  fi
  # stop any existing passport container
  ssh "${SATLAB_IP}" "${DOCKER_CMD}" rm -f "${PASSPORT_CONTAINER}" > /dev/null 2>&1
  # login to docker registry
  if ! ssh "${SATLAB_IP}" "${DOCKER_CMD} exec -i compose sh -c \
      'cat /home/satlab/keys/pubsub-key-do-not-delete.json \
      | /usr/local/bin/docker login -u _json_key --password-stdin\
       ${PASSPORT_DOCKER_REGISTRY}'"; then
    echo "ERROR: failed to login to docker registry, are you running this script on a satlab?"
    exit 1
  fi
  if ! ssh "${SATLAB_IP}" "${DOCKER_CMD} exec -i compose sh -c \
      \"/usr/local/bin/docker pull ${PASSPORT_DOCKER_IMAGE}\""; then
    echo "ERROR: failed to pull latest passport docker image"
    exit 1
  fi
  # start container
  echo -e "\n\nStarting passport container ${PASSPORT_DOCKER_IMAGE}..."
  if ! ssh "${SATLAB_IP}" "${DOCKER_CMD}" run \
    -d \
    --rm \
    --name ${PASSPORT_CONTAINER} \
    --privileged \
    -p 8300:8300 \
    "${PASSPORT_DOCKER_IMAGE}" ; then
    echo "ERROR: failed to start passport container"
    exit 1
  fi

  PASSPORT_IP="$(ssh "${SATLAB_IP}" "${DOCKER_CMD}" inspect -f \
    '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' \
    "${PASSPORT_CONTAINER}")"
  if [[ $? -ne 0 || -z "${PASSPORT_IP}" ]]; then
    echo -e "\n\nERROR: Failed to get Passport container IP."
    exit 1
  fi
}

function setup_servo() {
  local SERVO_CONTAINER_NAME
  local SERVO_SERIAL
  local DUT_INFO_FILE

  echo -e "\n\nStarting servod container..."
  DUT_INFO_FILE="$(mktemp)"
  if ! shivas get dut -json "${DUT_HOSTNAME}" > "${DUT_INFO_FILE}"; then
    echo -e "\n\nFailed to get DUT info from shivas for ${DUT_HOSTNAME}"
    echo "Please check if the DUT is a satlab DUT and that shivas command is installed, on your path and logged in."
    echo "You can try running the following command to validate shivas is working:"
    echo -e "\tshivas get dut ${DUT_HOSTNAME}"
    echo "You can login to shivas by running:"
    echo -e "\tshivas login"
    exit 1
  fi
  SERVO_SERIAL=$(jq -r '.. | .servoSerial? | select(. != null)' "${DUT_INFO_FILE}")
  if [[ $? -ne 0 || -z "${SERVO_SERIAL}" ]]; then
    echo -e "\n\nFailed to get servo serial for ${DUT_HOSTNAME}"
    echo "Please check if the DUT is a satlab DUT and that shivas is installed and logged in."
    echo "You can try running the following command to validate shivas is working:"
    echo -e "\tshivas get dut ${DUT_HOSTNAME}"
    exit 1
  fi

  SERVO_CONTAINER_NAME=$(jq -r '.. | .servoHostname? | select(. != null)' "${DUT_INFO_FILE}")
  if [[ -z "${SERVO_CONTAINER_NAME}" ]]; then
    SERVO_CONTAINER_NAME="${DUT_HOSTNAME}-docker_servod"
  fi
  rm "${DUT_INFO_FILE}"

  echo "Setting up servod for ${DUT_HOSTNAME}..."
  echo "Servo serial: ${SERVO_SERIAL}"
  echo "SERVO_CONTAINER_NAME: ${SERVO_CONTAINER_NAME}"
  echo "BOARD: ${BOARD}"
  echo "MODEL: ${MODEL}"

  run_command_on_satlab_ignore_error satlab servod stop -host "${DUT_HOSTNAME}" > /dev/null 2>&1
  if ! run_command_on_satlab satlab servod start -host "${DUT_HOSTNAME}" -board "${BOARD}" -model "${MODEL}" -servo-serial "${SERVO_SERIAL}" -servod-container-name "${SERVO_CONTAINER_NAME}"; then
    echo -e "\n\nFailed to start servod for ${DUT_HOSTNAME}"
    exit 1
  fi

  SERVO_IP="$(ssh "${SATLAB_IP}" /usr/local/bin/docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "${SERVO_CONTAINER_NAME}")"
  if [[ $? -ne 0 || -z "${SERVO_IP}" ]]; then
    echo -e "\n\nERROR: Failed to get Servod container IP."
    exit 1
  fi
  echo "SERVO_IP: ${SERVO_IP}"
}

function crosfleet_dut_info() {
  echo -e "\n\nGetting DUT info from crosfleet for ${DUT_HOSTNAME}..."
  local DUT_INFO_FILE
  DUT_INFO_FILE="$(mktemp)"
  if ! crosfleet dut info -json "${DUT_HOSTNAME}" > "${DUT_INFO_FILE}"; then
    echo -e "\n\nFailed to get DUT info from crosfleet for ${DUT_HOSTNAME}"
    exit 1
  fi
  BOARD=$(jq -r '.DUTs[].Machine.chromeosMachine.buildTarget' "${DUT_INFO_FILE}")
  MODEL=$(jq -r '.DUTs[].Machine.chromeosMachine.model' "${DUT_INFO_FILE}")
  POOL=$(jq -r '.. | .pools?[0] | select(. != null)' "${DUT_INFO_FILE}")
  rm "${DUT_INFO_FILE}"
  if [[ -z "${BOARD}" ]]; then
    echo -e "\n\nFailed to get board for ${DUT_HOSTNAME}"
    exit 1
  fi
  if [[ -z "${MODEL}" ]]; then
    echo -e "\n\nFailed to get model for ${DUT_HOSTNAME}"
    exit 1
  fi
  if [[ -z "${POOL}" ]]; then
    echo -e "\n\nFailed to get pool for ${DUT_HOSTNAME}"
    exit 1
  fi
}

function adb_connect_and_dut_info() {
  echo -e "\n\nConnecting to DUT ${DUT_HOSTNAME} via ADB..."
  if ! adb connect "localhost:${DUT_ADB_TUNNEL_PORT}"; then
    echo -e "\n\nFailed to connect to DUT ${DUT_HOSTNAME} via ADB"
    exit 1
  fi
  sleep 2
  adb -s "localhost:${DUT_ADB_TUNNEL_PORT}" shell getprop ro.build.fingerprint
  if [[ $? -ne 0 ]]; then
    echo -e "\n\nERROR: Failed to get DUT info via ADB. DUT may not be connected. or may not be running Android."
    exit 1
  fi
}

function generate_config() {
  if [[ -z "${CONFIG_OUTPUT_FILE}" ]]; then
    return
  fi
  TOPOLOGY_CONVERTER_CMD="topology_converter"
  if [[ -x ${SCRIPT_DIR}/topology_converter ]]; then
    # allow using prebuilt binary from shared prebuilt dir
    TOPOLOGY_CONVERTER_CMD="${SCRIPT_DIR}/topology_converter"
  elif  ! which topology_converter; then
    if [[ -z "${ANDROID_BUILD_TOP}" ]]; then
      echo -e "\n\n-c flag was provided and topology_converter is not installed"
      echo -e "\tEnsure this script is run from the android checkout directory,"
      echo -e "\tand ensure that the lunch command has been run to setup the environment"
      exit 1
    fi
    echo "Building topology_converter..."
    m topology_converter
    if [[ $? -ne 0 ]]; then
      echo -e "\n\nERROR: Failed to build topology_converter."
      exit 1
    fi
  fi
  echo -e "\n\nGenerating config yaml file for ${DUT_HOSTNAME}..."
  SHIVAS_JSON_FILE="$(mktemp --suffix .json)"
  if ! shivas get peripheral-pasit-host -dut "${DUT_HOSTNAME}" -json > "${SHIVAS_JSON_FILE}"; then
    echo -e "\n\nFailed to get pasit topology info from shivas for ${DUT_HOSTNAME}"
    exit 1
  fi
  if [[ "$(wc -l "${SHIVAS_JSON_FILE}" | awk '{print $1}')" -lt 6 ]]; then
    echo -e "\n\Not enough data in shivas pasit topology for ${DUT_HOSTNAME}"
    cat "${SHIVAS_JSON_FILE}"
    exit 1
  fi

  if ! "${TOPOLOGY_CONVERTER_CMD}" convert --ignore-unknown-fields --ignore-unknown-fields -i "${SHIVAS_JSON_FILE}" -o "${CONFIG_OUTPUT_FILE}"; then
    echo -e "\n\nFailed to generate config yaml file for ${DUT_HOSTNAME}"
    exit 1
  fi
  rm "${SHIVAS_JSON_FILE}"
  if [[ "${PORT_OFFSET}" -ne 0 ]]; then
    echo "Updating ports in config file with offset ${PORT_OFFSET}..."
    sed -i "s/5555/${DUT_ADB_TUNNEL_PORT}/g" "${CONFIG_OUTPUT_FILE}"
    sed -i "s/8300/${PASSPORT_TUNNEL_PORT}/g" "${CONFIG_OUTPUT_FILE}"
    sed -i "s/8080/${IP_POWER_SWITCH_TUNNEL_PORT}/g" "${CONFIG_OUTPUT_FILE}"
    sed -i "s/9999/${SERVOD_TUNNEL_PORT}/g" "${CONFIG_OUTPUT_FILE}"
  fi
  if [[ "${CROS_TESTING}" == true ]]; then
    echo "Modifying config file for CROS testing..."
    sed -i "s/AndroidDevice:.*/CrosDevice:\n    - hostname: localhost\n      custom_ssh_port: ${DUT_SSH_TUNNEL_PORT}/" "${CONFIG_OUTPUT_FILE}"
  fi
}

function lease_dut() {
  echo -e "\n\nChecking if DUT ${DUT_HOSTNAME} is leased..."
  #check that DUT is leased and if not lease it
  if ! crosfleet dut leases | grep -q "${DUT_HOSTNAME}"; then
    if [[ "${PROVISION}" == true ]]; then
      RUN_TYPE="suite"
      OS_SPECIFIC_ARGS="-desktop -test-name-includes tradefed.cts.CtsJvmtiRunTest1911HostTestCases crosfleet-placeholder"
      if [[ "${CROS_TESTING}" == true ]]; then
        RUN_TYPE="test"
        OS_SPECIFIC_ARGS="-harness tast example.Pass"
      fi
      echo -e "\n\nDUT ${DUT_HOSTNAME} is not leased, provisioning before leasing ...\n\n"
      crosfleet run ${RUN_TYPE} \
        -board "${BOARD}" \
        -pool "${POOL}" \
        -dims "dut_name:${DUT_HOSTNAME}" \
        ${OS_SPECIFIC_ARGS}
      if [[ $? -ne 0 ]]; then
        echo -e "\n\nERROR: Failed to provision DUT ${DUT_HOSTNAME}."
        exit 1
      fi
      echo -e "\n\nDUT ${DUT_HOSTNAME} is not leased, waiting 3 minutes for provisioning to start before leasing ..."
      sleep 180
    fi
    echo -e "\n\nDUT ${DUT_HOSTNAME} is not leased, leasing now..."
    crosfleet dut lease -minutes "${DUT_LEASE_MINUTES}" -host "${DUT_HOSTNAME}"
    if [[ $? -ne 0 ]]; then
      echo -e "\n\nERROR: Failed to lease DUT ${DUT_HOSTNAME}."
      exit 1
    fi
  fi
}

# parse the arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      ;;
    --cros)
      CROS_TESTING=true
      shift
      ;;
    -d|--dut_hostname)
      DUT_HOSTNAME="$2"
      shift; shift
      ;;
    -s|--satlab_ip)
      SATLAB_IP="$2"
      shift; shift
      ;;
    -p|--provision)
      PROVISION=true
      shift
      ;;
    -m|--minutes)
      DUT_LEASE_MINUTES="$2"
      shift; shift
      ;;
    -c|--config-generate)
      CONFIG_OUTPUT_FILE="$2"
      shift; shift
      ;;
    --skip-lease)
      SKIP_LEASE=true
      shift
      ;;
    --skip-servo-setup)
      SKIP_SETUP_SERVO=true
      shift
      ;;
    --port-offset)
      PORT_OFFSET="$2"
      shift; shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

if [[ -z "${DUT_HOSTNAME}" ]]; then
  usage
fi

if [[ -z "${SATLAB_IP}" ]]; then
  echo -e "Missing Satlab IP, please provide it with the -s|--satlab_ip flag.\n\n"
  echo "You can find the IP of your Satlab in the 'drone_server' entry under Dimensions by clicking the link below:"
  echo "go/fcdut/${DUT_HOSTNAME}?tab=bot-info"
  exit 1
fi

if [[ "${PORT_OFFSET}" -ne 0 ]]; then
  echo "Using port offset: ${PORT_OFFSET}"
  DUT_ADB_TUNNEL_PORT=$((DUT_ADB_TUNNEL_PORT + PORT_OFFSET))
  PASSPORT_TUNNEL_PORT=$((PASSPORT_TUNNEL_PORT + PORT_OFFSET))
  DUT_SSH_TUNNEL_PORT=$((DUT_SSH_TUNNEL_PORT + PORT_OFFSET))
  IP_POWER_SWITCH_TUNNEL_PORT=$((IP_POWER_SWITCH_TUNNEL_PORT + PORT_OFFSET))
  SERVOD_TUNNEL_PORT=$((SERVOD_TUNNEL_PORT + PORT_OFFSET))
fi

check_dependencies
# Check SSH access early
check_ssh_access

if [[ "${SKIP_LEASE}" != true || "${SKIP_SETUP_SERVO}" != true || "${PROVISION}" == true ]]; then
  # if we are not doing these steps then we can skip the crosfleet call
  # since we won't need the DUT info for anything else this removes the need
  # for crosfleet and shivas commands
  crosfleet_dut_info
  echo "Setting up DUT board: ${BOARD}, model: ${MODEL}, pool: ${POOL}"
fi

echo -e "\n\nChecking if satlab ${SATLAB_IP} is logged in..."
# check that we can ssh to the satlab and that we are logged in
WHOAMI="$(run_command_on_satlab satlab whoami 2>&1)"
if [[ "${WHOAMI}" =~ "Not logged in." ]]; then
  echo -e "\n\nYou are not logged in to satlab ${SATLAB_IP} please follow steps below to login:\n\n"

  echo "satlab login ${SATLAB_IP}"
  if ! run_command_on_satlab satlab login; then
    echo -e "\n\nFailed to login to satlab ${SATLAB_IP}"
    exit 1
  fi
fi

if [[ "${SKIP_LEASE}" != true ]]; then
  lease_dut
fi
generate_config
start_passport
if [[ "${SKIP_SETUP_SERVO}" != true ]]; then
  setup_servo
fi
setup_tunnel
if [[ "${CROS_TESTING}" == true ]]; then
  echo -e "\n\nReady to run CrOS tests on DUT with ssh localhost:${DUT_SSH_TUNNEL_PORT}..."
else
  adb_connect_and_dut_info
  echo -e "\n\nReady to run Android tests on DUT with adb serial loclahost:${DUT_ADB_TUNNEL_PORT}..."
  echo "see go/write-pasit-test for more details."
fi