---
id: T-4464
title: 'release.yml: manylinux wheels fail to import (le16toh) and the Windows wheel
  smoke uses bin/python'
state: done
kind: bug
origin: agent
created: '2026-09-13'
priority: critical
parent: null
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/release.yml
- tests/unit/test_release_workflow_gate.py
- docs/guides/release.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: BUG002 confirmatory-only at land; CI-config-only change, same posture as
    T-4450/T-4462
  actor: logan
  at: '2026-09-13'
  old_length: 2053
  new_length: 2447
evidence:
- tests/unit/test_release_workflow_gate.py::TestManylinuxPinAndWindowsSmoke::test_manylinux_targets_pin_2_28
- tests/unit/test_release_workflow_gate.py::TestManylinuxPinAndWindowsSmoke::test_manylinux_pin_reason_is_documented
- tests/unit/test_release_workflow_gate.py::TestManylinuxPinAndWindowsSmoke::test_smoke_step_is_os_aware
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Release run 34769124533 (dispatched 2026-09-13 on tag v0.531.0 = abd79f23f with the T-3251 override): build-sdists, verify-ci-status and the macos-arm64 wheel build passed; THREE build matrix jobs failed in the step "Install the just-built wheels into a clean venv and import them" (.github/workflows/release.yml ~line 121), so no upload-* job can start. (1) manylinux-x86_64 and manylinux-aarch64 (maturin-action, manylinux: auto): `ImportError: .../frob_core/frob_core.abi3.so: undefined symbol: le16toh`. tree-sitter 0.25.10's C library (its lib/src/portable/endian.h shim includes <endian.h> and uses le16toh) is compiled by the crate's build.rs with -std=c11 and -D_DEFAULT_SOURCE; on the manylinux2014 container (glibc 2.17) `_DEFAULT_SOURCE` does not exist yet (glibc 2.19 introduced it) and under -std=c11 the endian macros stay hidden, so le16toh becomes an implicit function and an undefined symbol at load. This does not affect ci.yml because `make core` builds on ubuntu-latest's glibc 2.39. FIX: pin `manylinux: 2_28` for both Linux targets (glibc 2.28 defines the macros under _DEFAULT_SOURCE), OR pass `CFLAGS=-D_BSD_SOURCE -D_DEFAULT_SOURCE` via maturin-action's env for the manylinux jobs; prefer 2_28 and document why in the workflow comment. (2) windows-x86_64: `error: No virtual environment or system Python installation found for path C:/Users/RUNNER~1/AppData/Local/Temp/native-check-venv/bin/python` -- the smoke step hardcodes the POSIX venv layout (bin/python); on Windows uv creates Scripts/python.exe. FIX: compute the interpreter path per RUNNER_OS in the bash step (Scripts/python.exe on Windows, bin/python elsewhere) and put the venv under "$RUNNER_TEMP". ACCEPTANCE: (a) tests/unit/test_release_workflow_gate.py asserts the manylinux jobs pin 2_28 (or the CFLAGS) and the smoke step is OS-aware; (b) a re-dispatch of release.yml builds and import-smokes all five targets green; (c) docs/guides/release.md notes the manylinux floor and why. Sprint v0.531.0 (release blocker). Do NOT touch any upload-* job or environment.

frob:waive BUG002 reason="CI-config-only change: release.yml's manylinux pin (2_28) and the OS-aware wheel import-smoke step are measurable only on the release runners (run 34769124533 shows the le16toh ImportError on manylinux and the bin/python OpenError on Windows); the bound workflow-assertion tests pass at the parent by construction (T-2025 shape, test and fix squash-land together)."