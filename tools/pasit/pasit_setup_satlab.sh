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


# constants
DUT_LEASE_MINUTES=120
DUT_ADB_TUNNEL_PORT=5555
PASSPORT_TUNNEL_PORT=8300
IP_POWER_SWITCH_TUNNEL_PORT=8080
SERVOD_PORT=9999
IP_POWER_SWITCH_IP="192.168.231.110"

PASSPORT_DOCKER_REGISTRY="us-docker.pkg.dev/cros-passport"
PASSPORT_DOCKER_IMAGE="${PASSPORT_DOCKER_REGISTRY}/passport/passport:latest"
PASSPORT_CONTAINER="passport-dev"


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
  echo ""
  echo "Example:"
  echo "  pasit_setup_satlab.sh -d <DUT_HOSTNAME> -s <SATLAB_IP> [-c /path/to/config.yaml]"
  exit 1
}

function run_command_on_satlab() {
  # runs command on satlab in a bash shell so that we get env vars
  # and path as if we were running command from interactive shell
  # this assumes that no variable expanision is needed on the remote
  # ssh shell
  ssh "${SATLAB_IP}" -t "bash -l -c '$*'"
}

function setup_tunnel() {
  TUNNEL_PGREP="ssh -fNT -L.*"
  echo "Killing existing tunnels to satlab-*..."
  pgrep -f "${TUNNEL_PGREP}" | xargs kill -9 > /dev/null 2>&1
  # background tunnel to the DUT
  if [[ ! -z "${SERVO_IP}" ]]; then
    SERVO_TUNNEL="-L ${SERVOD_PORT}:${SERVO_IP}:${SERVOD_PORT}"
  fi
  # shellcheck disable=SC2086
  ssh -fNT \
    -L "${DUT_ADB_TUNNEL_PORT}:${DUT_HOSTNAME}:5555" \
    -L "${PASSPORT_TUNNEL_PORT}:${PASSPORT_IP}:8300" \
    -L "${IP_POWER_SWITCH_TUNNEL_PORT}:${IP_POWER_SWITCH_IP}:80" \
    ${SERVO_TUNNEL} \
    "${SATLAB_IP}"
  sleep 5
  # check if the tunnel is up
  if ! pgrep -f "${TUNNEL_PGREP}" > /dev/null 2>&1; then
    echo -e "\n\nFailed to start SSH tunnel to ${SATLAB_IP}"
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
    # exit 1
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
  if [[ -z "${SERVO_SERIAL}" ]]; then
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

  run_command_on_satlab satlab servod stop -host "${DUT_HOSTNAME}" > /dev/null 2>&1
  if ! run_command_on_satlab satlab servod start -host "${DUT_HOSTNAME}" -board "${BOARD}" -model "${MODEL}" -servo-serial "${SERVO_SERIAL}" -servod-container-name "${SERVO_CONTAINER_NAME}"; then
    echo -e "\n\nFailed to start servod for ${DUT_HOSTNAME}"
    exit 1
  fi

  SERVO_IP="$(ssh "${SATLAB_IP}" /usr/local/bin/docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "${SERVO_CONTAINER_NAME}")"
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
  adb -s "localhost:${DUT_ADB_TUNNEL_PORT}" shell getprop ro.build.fingerprint
}

function generate_config() {
  if [[ -z "${CONFIG_OUTPUT_FILE}" ]]; then
    return
  fi
  if  ! which topology_converter; then
    if [[ -z "${ANDROID_BUILD_TOP}" ]]; then
      echo -e "\n\n-c flag was provided and topology_converter is not installed"
      echo -e "\tEnsure this script is run from the android checkout directory,"
      echo -e "\tand ensure that the lunch command has been run to setup the environment"
      exit 1
    fi
    echo "Building topology_converter..."
    m topology_converter
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

  if ! topology_converter convert -i "${SHIVAS_JSON_FILE}" -o "${CONFIG_OUTPUT_FILE}"; then
    echo -e "\n\nFailed to generate config yaml file for ${DUT_HOSTNAME}"
    exit 1
  fi
  rm "${SHIVAS_JSON_FILE}"
}

function lease_dut() {
  echo -e "\n\nChecking if DUT ${DUT_HOSTNAME} is leased..."
  #check that DUT is leased and if not lease it
  if ! crosfleet dut leases | grep -q "${DUT_HOSTNAME}"; then
    if [[ "${PROVISION}" == true ]]; then
      echo -e "\n\nDUT ${DUT_HOSTNAME} is not leased, provisioning before leasing ...\n\n"
      crosfleet run suite \
        -desktop \
        -board "${BOARD}" \
        -pool "${POOL}" \
        -dims "dut_name:${DUT_HOSTNAME}" \
        -test-name-includes tradefed.cts.CtsJvmtiRunTest1911HostTestCases \
        crosfleet-placeholder
      echo -e "\n\nDUT ${DUT_HOSTNAME} is not leased, waiting 3 minutes for provisioning to start before leasing ..."
      sleep 180
    fi
    echo -e "\n\nDUT ${DUT_HOSTNAME} is not leased, leasing now..."
    crosfleet dut lease -minutes "${DUT_LEASE_MINUTES}" -host "${DUT_HOSTNAME}"
  fi
}

# parse the arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
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
  echo "You can find the IP of your Satlab in the 'drone_server' entry of the following link:"
  echo "https://chromeos-swarming.appspot.com/bot?id=crossk-${DUT_HOSTNAME}"
  exit 1
fi

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
adb_connect_and_dut_info

echo -e "\n\nReady to run Android tests on DUT with adb serial loclahos:${DUT_HOSTNAME}..."
echo "see go/satlab-local-pasit for more details"
