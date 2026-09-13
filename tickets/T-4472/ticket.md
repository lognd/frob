---
id: T-4472
title: 'release.yml: cross-built targets still run uv pip install before the T-4470
  cross skip, failing the smoke step'
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'waive BUG002: TEST_ABSENT_AT_PARENT (test written for this ticket, CI-config
    change with no local repro path)'
  actor: logan
  at: '2026-09-13'
  old_length: 1424
  new_length: 2758
evidence:
- tests/unit/test_release_workflow_gate.py::TestCrossBuiltTargetsSkipImportSmoke::test_install_only_runs_inside_the_non_cross_branch
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Release run 34786316434 (tag v0.531.0 = e16d97290, includes T-4470): both cross-built matrix entries (macos-x86_64 on macos-latest, manylinux-aarch64 on ubuntu-latest) still fail the step "Install the just-built wheels into a clean venv and import them" with uv's "error: Failed to determine installation plan ... dependency is incompatible with the current platform". T-4470's `if [ "${{ matrix.cross }}" = "true" ]` branch is correct but sits AFTER the unconditional `uv pip install --python "$python_bin" frob-core/dist/*.whl strata-core/dist/*.whl`, and it is the INSTALL that rejects a foreign-architecture wheel, so the skip is never reached (the step log shows the venv created, then the install failing, the echo never printed). FIX: move the `uv pip install` (and the venv creation) inside the non-cross branch; cross entries only list the wheels (and may sanity-check the wheel filename's platform tag against the matrix target with a plain string test). Update tests/unit/test_release_workflow_gate.py's TestCrossBuiltTargetsSkipImportSmoke to assert the install command appears only inside the non-cross branch (parse the run script: the `uv pip install` line must come after the `if ... cross` test and before its `else`, or be absent from the cross path). ACCEPTANCE: the next release dispatch builds all five targets green and reaches upload-frob-core. Sprint v0.531.0 (release blocker, follow-up to T-4470).



frob:waive BUG002 reason="test added and fixed in the same commit (this ticket's own worktree, not a squash), so --check-repro against the ticket-start parent (57d70126e) reports TEST_ABSENT_AT_PARENT: 'no tests ran', not a pass or a fail -- the test does not exist there at all, by construction, since it was written for this ticket. This is a CI-config change (.github/workflows/release.yml matrix run-script edit) with no local runtime path to fail-before/pass-after on this host either way: there is no way to execute a GitHub-hosted-runner cross-arch uv pip install locally. The designated node id (test_install_only_runs_inside_the_non_cross_branch, frob:tests T-4472) asserts against the REAL workflow YAML's run script, parsing the if/else structure and verifying uv pip install/uv venv appear only in the non-cross arm; it PASSES post-fix and would FAIL against the pre-fix script (uv pip install was unconditional, before the if). The actual defect (release run 34786316434, post-T-4470 land e16d97290: both cross entries failed install with 'Failed to determine installation plan ... incompatible with the current platform' because uv pip install ran before the matrix.cross skip check) is documented in this ticket's body and in the workflow comment; the fix moves venv creation + install inside the non-cross branch."