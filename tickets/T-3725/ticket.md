---
id: T-3725
title: fix frob doctor CI exit-1 on git-hooks-absent
state: queued
kind: bug
origin: human
created: '2026-09-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/doctor.py
- src/frob/app/doctor_runner.py
- .github/workflows/ci.yml
- tests/unit/test_doctor.py
- tests/unit/test_doctor_runner_t1276.py
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
CI run 33715737237 ubuntu job: SUITE-RESULT exitstatus=0 (13334 passed), self-gate 0 errors, but the T-1366 coverage-stamp step (.github/workflows/ci.yml ~1556-1650) fails at 'uv run frob doctor' under bash -e. Root cause: _doctor_healthy in src/frob/doctor.py hard-fails (exit 1) when scaffold_needs_apply is non-empty -- CI checkouts never install frob's LOCAL managed git hooks (.git/hooks/pre-commit etc, T-0736 scaffold), so this is a structural CI false-positive, not a real health failure. Separately, doctor_runner.py's plain renderer prints the generic label 'native extensions missing' whenever ANY health check fails (not just extension unavailability), which misleadingly blamed extensions in the CI log even though frob_core/strata_core both reported available=True (version=unknown is just an unset __version__ attribute, not a misclassification -- _extension_status already treats available=True as healthy regardless of version string). Fix: (1) make scaffold/git-hook staleness informational (does not fail healthy/exit code), matching how drift/live_land_process(alive=True) are already informational; still surfaced in remediation/plain output. (2) fix the misleading 'native extensions missing' label to only print when natives are actually unhealthy.