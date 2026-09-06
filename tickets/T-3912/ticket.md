---
id: T-3912
title: DEPR003 fires as error severity in frob check --json despite being documented
  as WARN while in its sunset window
state: in-progress
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- frob.toml
- tests/gates_suite/test_depr003_severity_override.py
- tests/gates_suite/test_compliance.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: frob.toml
  reason: smallest correct fix is reverting the config override, not the gate code
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/gates_suite/test_debt.py
  reason: regression test for the frob.toml severity-override fix
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: src/frob/gates/_debt_deprecated.py
  reason: fix lives entirely in frob.toml's severity override; this file was never
    modified, its scope-closure edges (docs/tests fan-out) do not apply
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: tests/gates_suite/test_debt.py
  reason: moved regression tests into a dedicated new file to avoid pulling in test_debt.py's
    large pre-existing cross-reference fan-out
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/gates_suite/test_depr003_severity_override.py
  reason: moved regression tests into a dedicated new file to avoid pulling in test_debt.py's
    large pre-existing cross-reference fan-out
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/gates_suite/test_compliance.py
  reason: 'SCOPE002 false-positive: bare-short-name call-graph resolution matches
    this test''s own _write helper (a class method) to my imported tests.conftest._write
    of the same short name; not a real dependency, widened to unblock close (see filed
    follow-up)'
  actor: logan
  at: '2026-09-05'
evidence:
- tests/gates_suite/test_depr003_severity_override.py::test_depr003_survives_repo_severity_overrides
- tests/gates_suite/test_depr003_severity_override.py::test_depr003_not_forced_to_error_in_this_repo
designated_repro_test: null
evidence_changes:
- old_node: tests/gates_suite/test_debt.py::TestDeprecatedGate::test_depr003_survives_repo_severity_overrides
  new_node: tests/gates_suite/test_depr003_severity_override.py::test_depr003_survives_repo_severity_overrides
  reason: moved test into a dedicated file to avoid test_debt.py's scope-closure fan-out
  actor: logan
  at: '2026-09-05'
- old_node: tests/gates_suite/test_debt.py::TestDeprecatedGate::test_depr003_not_forced_to_error_in_this_repo
  new_node: tests/gates_suite/test_depr003_severity_override.py::test_depr003_not_forced_to_error_in_this_repo
  reason: moved test into a dedicated file to avoid test_debt.py's scope-closure fan-out
  actor: logan
  at: '2026-09-05'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3906 added this repo's first LIVE frob:deprecated directive (src/frob/app/fmt_runner.py::run, sunset 2026-12-01, well in the future). _depr003_violations builds its Violation with severity=Severity.WARN (see the function's own docstring: 'a WARNING, kept visible ... rather than silent until the sunset date arrives'), yet frob check --json reports it with severity: "error" (measured directly in the raw JSON diagnostic, not through a summary script). Either _depr003_violations's WARN severity is being overridden somewhere between gate evaluation and JSON serialization, or a different code path (DEPR004's expired-severity branch?) is firing despite the sunset date not having passed. MUST-FIRE: a fresh frob:deprecated directive with sunset in the future reports severity warn in frob check --json's raw diagnostic. MUST-STAY-QUIET: an expired one (DEPR004) still reports severity error.