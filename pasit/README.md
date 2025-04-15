# PASIT Mobly Tests

These suites of tests allow for testing peripherals with Desktop devices using
PASIT (go/pasit-prd) testbeds.  The tests are [mobly] host side tests which
use [passport] service to control the peripherals.

The following docs assume you have an Android checkout and have run the `lunch`
command to setup a build target.  Since these are hostside tests in most cases
you do not need to use the exact build target you are testing, however the build
target architecture must match the architecture of the DUT you are testing.

## Building

To build:

```
m <PASIT suite build target name>
# artifacts in
# ./out/host/linux-x86/nativetest64/<PASIT suite build target name>/<PASIT suite build target name>
# example:
m DesktopPASITStorageTests
ls ./out/host/linux-x86/nativetest64/DesktopPASITStorageTests/DesktopPASITStorageTests
```

## Running

You must have the [passport] service setup and running on your test host, and
have a testbed and `config.yaml` for your testbed before you can run PASIT tests.

### Running with `atest`

Using `atest` is the simplest method as it will build all the required
dependencies and execute the test in one command.  Since PASIT uses configurable
testbeds that vary in the args and setup, you cannot use the generated
`config.yaml` from `atest` and must pass one as an argument.

```
# run an entire suite
atest <PASIT suite build target name> [--iterations <num iterations] -- --config <path to your config> --testbed <name of testbed from config>
# example
atest DesktopPASITStorageTests --iterations 20 -- --config ~/pasit_local.yaml --testbed LocalAndroidTestbed
```

When running a PASIT suite you can filter by test case with the syntax
`MODULE:CLASS#TESTCASE1,TESTCASE2...`.  Test case is optional, so you can filter
by class or test cases within a class.  With `atest` you cannot filter to run
multiple classes in a single `atest` command.

```
# example run a single test case
atest DesktopPASITMiscTests:PassportHostTest#test_get_switches DesktopPASITMiscTests:HelloWorldTest -- --config ~/pasit_local.yaml --testbed LocalAndroidTestbed
```

### Running the test binary directly

You can also run the binary directly, if re-running frequently without changing
the code this will be faster as it doesn't require waiting for `soong` to check
for changes and can execute immediately.

```
# ./out/host/linux-x86/nativetest64/<PASIT suite build target name>/<PASIT suite build target name>
./out/host/linux-x86/nativetest64/DesktopPASITStorageTests/DesktopPASITStorageTests -c ~/pasit_local.yaml
```

Filters can be passed similar to `atest`, using the `--tests` flag. Similar to
`atest` you can specify class and or test case though note below syntax is
slightly different. Multiple filters can be passed by surrounding with quotes
and separating the filters with spaces, allowing filtering of multiple classes
or test cases.

```
./out/host/linux-x86/nativetest64/DesktopPASITStorageTests/DesktopPASITStorageTests -c ~/pasit_local.yaml  --tests EjectExternalStorageTest.test_write
```

Note if you have only one testbed config in your config file you do not need to
specify the testbed otherwise you can use `--test_bed`. For more details on args
that can be passed use the `-h` arg to your test binary.

[mobly]: https://github.com/google/mobly
[passport]: https://chromium.googlesource.com/chromiumos/platform/passport/+/main/README.md