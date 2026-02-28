---
name: pasit-runner
description: Run PASIT Mobly tests using atest and lease DUTs for PASIT tests.
Use when the user needs to execute peripheral tests (camera, display, storage)
on a Desktop Android DUT.
---

# PASIT Test Runner

This skill guides you through setting up a PASIT DUT and running Mobly tests
using the automated `run_pasit_test.sh` script.

## Workflow

### 1. Information Gathering

Ask the user for:

-   The **DUT name** (e.g., `satlab-XYZ`).
-   The **Test Target** (e.g., `DesktopPASITStorageTests[:class name[#method
    name]]` ).
-   Gather any specific test methods or iterations if needed.

### 2. Execution

Use the `run_pasit_test.sh` script to automate setup, and test execution:

```bash
# Path relative to the skill directory or absolute if known
# The agent will resolve this automatically.
./scripts/run_pasit_test.sh -d <DUT_NAME> -t <TEST_TARGET> [options]
```

-   **Flags**:
    -   `-d <DUT_NAME>`: Hostname of the DUT.
    -   `-t <TEST_TARGET>`: atest module (with optional class and method)
        `<TestModule>[:class name[#test method]]` eg
        `DesktopPASITDisplayTests:PlugInExternalDisplayTest#test_plug_in_display_when_dut_on_dock`
    -   `-i <N>`: Run the test N times.
    -   `--skip-setup`: Use if tunnels and config are already established or
        re-running a test.

## Reference

See [references/setup_guide.md](references/setup_guide.md) for detailed commands
and troubleshooting.
