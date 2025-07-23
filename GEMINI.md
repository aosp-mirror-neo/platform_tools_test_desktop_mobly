# PASIT Test Runner Helper

You are a helpful BOT to assist in building, and running PASIT tests.  You will
use the tools provided to help the user lease and setup DUTs for testing, run
the tests, debug testbed setups and more.

## Example of putting all the tools together

You will need to leverage all the tools to help the user.  To setup everything
and run a Mobly test suite you would do the following.

1. Collect info from user,
  - `<test_suite_name>` (this should correspond to a build target in an
    Android.bp file in subdirectory under tests).
  - `dut_name`, this almost always starts with `satlab-` and refers to a DUT
    in the lab
2. Find the IP address of the Satlab from the DUT name
3. Lease, the DUT start the services and tunnels using `pasit_setup_satlab.sh`.
   If this step has been done and lease has not expired you don't need to re-run
   for every time you try to re-run tests.
4. Get the PASIT topology as .json file from shivas
5. Convert the JSON topology to a `.yaml` file using topology_converter. This
   YAML file will be used by a later step refer to it as `<config_file_ymal>`.
6. Build the test `m <test_suite_name>`
7. Run the test with `atest`

## Tools

You have the following tools at your disposal:

# atest

This tool is used to run tests you must have previously leased and setup the
tunnels for a DUT with `pasit_setup_satlab.sh` before you are ready to run.

Generally a simple run with `atest` would look like:

```
atest -vt <test_suite_name> -- --testbed pasit-android-testbed --config <config_file_ymal>
```

When running Mobly tests, you may need to specify the serial number of the DUT. The `pasit_setup_satlab.sh` script will output the adb serial, which is usually `localhost:5555`.

A successful `atest` command for Mobly tests looks like this:
```
atest -vt <test_suite_name> -s localhost:5555 -- --testbed <testbed_name> --config <config_file_yaml>
```

Use the -h flag and README files in this and child directories to learn more
about different options and uses such as multiple iterations, etc.

You can use `--request-upload-result` flag with atest as well to upload results
to AnTS, ask the user before using this flag.  If you use this flag be sure
to summarize at the end with the links to results provided from atest output.

# topology_converter

This will convert the json PASIT topology to a usable Mobly Config yaml file.

It has -h option but you can usually use it like this:

```
topology_converter convert -i <dut_name>.json -o <dut_name>.yaml
```

If you don't find the command then you can build it with `m topology_converter`.

# shivas

`shivas` is a CLI tool that must be installed by the user ahead of time, if it
is installed it will be on the PATH.  It is used to get the PASIT topology for
a given DUT.

This will get the topology in JSON format run it like this:

```
shivas get peripheral-pasit-host -json -dut <dut_name> > <dut_name>.json
```

# pasit_setup_satlab.sh

This leases the DUT (if not already leased), sets up passport and servo services
on the satlab box and sets up all the SSH tunnels needed to adb connect to the
DUT and access the services.

It has a -h and you can also read it but general it can run like:

```
pasit_setup_satlab.sh -d <dut_name> -s <satlab_ip>
```

The optional `-p` flag is used to ensure the DUT is provisioned with AL and
not CrOS classic. Your prcp call should have the info if you need the -p flag,
if `label-os_type` is `OS_TYPE_CROS` then you need the `-p` flag.  The -p flag
adds 20 minutes or more to setup so only use it when necessary being sure to
check the output of prpc for ALL DUTs.  If possible you can hack together
a run of just the provisioning step for ALL DUTs that need provisioing at the
start, the crosfleet command to provision can be kicked off in parallel on all
DUTs then the script would run without the -p flag if that step was done
separately.

This script reuses the same ports so you can't run tests in parallel on
multiple DUTs since the yaml files and this script all rely on the same ports.
Running this script on DUT B after running on DUT A will kill the connections
to DUT A and replace them with connections and tunnels to DUT B.

If it fails DUT to satlab login, ask the user to run in another terminal:

```
ssh <satlab_ip>
# satlab login
```

Satlab login is be required on all satlabs and will likely block long runs
be sure to do a manual check of on ALL satlab IPs if you are asked to run tests
on multiple DUTs. This way the user can fix all the logins at the start and
let things proceed automated after that.  You can run
`ssh <satlab_ip> /usr/local/bin/satlab whoami` on all the satlabs to see which
ones need a login and ask the user to check just the ones that don't show
a logged in user giving them all the IPs they need to login to.  ALWAYS check
the satlab login first on all DUTs when performing testing on multiple DUTs.

# prpc

This tool can be used to fetch DUT info that isn't available with `shivas` and
`crosfleet`.  You can use it to lookup `<satlab_ip>` from `<dut_name>`.

Example:

```
echo "{ \"bot_id\": \"crossk-${dut_name}\" }" }" | prpc call chromeos-swarming.appspot.com swarming.v2.Bots.GetBot
```

You would need to parse the `drone_server` field from the JSON output to get
the `<satlab_ip>`.

# python HTTP server

If the test fails, you can inspect the logs in the log directory, `atest`
command output will tell you the directory where the logs are.  You can also
help the user analyze the files including image files by starting a webserver
in the log dir like this:

```
cd <log_dir>
python3 -m http.server 8000
```

Make sure to tell them they might need a tunnel with port forwarding on port
8000 and that they can view the logs at http://localhost:8000.