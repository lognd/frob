---
id: T-3314
title: Scaffolded CI silently skips frob check when frob graph --help fails
state: done
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/data/shared/python/github/ci.yml.j2
- src/frob/scaffold/data/types/pyo3-library/github/ci.yml.j2
- src/frob/scaffold/data/types/web-app/github/ci.yml.j2
- tests/unit/test_scaffold_project.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_scaffold_project.py
  reason: T-3314's fix needs its own regression test (already present, verifying the
    loud-failure behavior across all three templates)
  actor: logan
  at: '2026-08-29'
evidence:
- tests/unit/test_scaffold_project.py::test_ci_template_frob_check_gate_fails_loudly_not_silently
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 69293de00308e1f9a6ee80646d744bd9eaff4e0c
---
T-3276 found this while auditing tool-missing handling: all three scaffolded GitHub Actions CI templates guard the frob check step with 'if command -v frob >/dev/null 2>&1 && frob graph --help >/dev/null 2>&1; then ... else echo ::notice::...; fi' -- a failed preflight emits a GitHub Actions notice annotation and SKIPS the frob check step entirely, rather than failing the job. A skipped gate that only reports a notice is indistinguishable from a passing gate in a green CI build (the same silent-degrade class T-3276 fixed for frob doctor/coverage). Make the missing-frob case fail the job loudly, or at minimum make the skip visible as a non-green CI status, not just an easily-missed notice line.