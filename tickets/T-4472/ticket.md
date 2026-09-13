---
id: T-4472
title: 'release.yml: cross-built targets still run uv pip install before the T-4470
  cross skip, failing the smoke step'
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Release run 34786316434 (tag v0.531.0 = e16d97290, includes T-4470): both cross-built matrix entries (macos-x86_64 on macos-latest, manylinux-aarch64 on ubuntu-latest) still fail the step "Install the just-built wheels into a clean venv and import them" with uv's "error: Failed to determine installation plan ... dependency is incompatible with the current platform". T-4470's `if [ "${{ matrix.cross }}" = "true" ]` branch is correct but sits AFTER the unconditional `uv pip install --python "$python_bin" frob-core/dist/*.whl strata-core/dist/*.whl`, and it is the INSTALL that rejects a foreign-architecture wheel, so the skip is never reached (the step log shows the venv created, then the install failing, the echo never printed). FIX: move the `uv pip install` (and the venv creation) inside the non-cross branch; cross entries only list the wheels (and may sanity-check the wheel filename's platform tag against the matrix target with a plain string test). Update tests/unit/test_release_workflow_gate.py's TestCrossBuiltTargetsSkipImportSmoke to assert the install command appears only inside the non-cross branch (parse the run script: the `uv pip install` line must come after the `if ... cross` test and before its `else`, or be absent from the cross path). ACCEPTANCE: the next release dispatch builds all five targets green and reaches upload-frob-core. Sprint v0.531.0 (release blocker, follow-up to T-4470).
