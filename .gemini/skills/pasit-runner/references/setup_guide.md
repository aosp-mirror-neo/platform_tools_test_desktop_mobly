# PASIT Setup and Runner Guide

## 1. Automated Execution (Recommended)

The `run_pasit_test.sh` script performs all the setup for PASIT tests. It
handles:

-   **Leasing**: Ensures the DUT is leased via `crosfleet`.
-   **Tunnels**: Sets up SSH tunnels to the Satlab and DUT.
-   **Config Generation**: Generates `mobly_config_<DUT>.yaml` from `shivas`
    topology.
-   **Execution**: Runs `atest` with the correct testbed and config.

### Basic Usage

```bash
./tools/pasit/run_pasit_test.sh -d <DUT_NAME> -t <TEST_TARGET>
```

DO NOT run envsetup.sh or lunch as they are slow, the user should run them
with terminal mode or before launching Gemini CLI.

### Iterations

```bash
./tools/pasit/run_pasit_test.sh -d <DUT_NAME> -t <TEST_TARGET> -i 5
```

## 4. Troubleshooting Determinism

-   **Lease Expired**: `crosfleet dut leases` to check.
-   **Tunnel Conflict**: Only one test can run at a time if someone else is
    using the same device/tunnels there will be unpredictable behavior.
-   **Config Mismatch**: If the hardware changed, delete the old
    `mobly_config_<DUT>.yaml` and re-run.
