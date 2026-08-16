---
id: T-2224
title: Via-less grants on fail-closed capability kinds (exec/eval/install-hook/ffi)
  are WARN-only, never enforced
state: done
kind: security
origin: human
created: '2026-08-16'
priority: critical
parent: T-1623
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/strata/_selfconform.py
- design/frob.strata
- docs/strata/selfconform.md
- src/frob/gates/_sys_selfaudit.py
- tests/unit/gates/test_sys_selfaudit.py
- tests/unit/strata/test_sys107_via_scope_advisory.py
- docs/strata/surface.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_sys_selfaudit.py
  reason: 'MEASURED: _selfaudit_severity (src/frob/gates/_sys_selfaudit.py:29) is
    the ONLY place that turns SYS107 into WARN vs ERROR -- _selfconform.py''s _via_less_large_node_violations
    only ever produces a rule=SYS107 SelfConformViolation with no severity of its
    own; severity is decided entirely in this gate-wiring file, which the ticket''s
    three declared scope files do not include'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/unit/gates/test_sys_selfaudit.py
  reason: test evidence for the severity-escalation change in _selfaudit_severity
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/unit/strata/test_sys107_via_scope_advisory.py
  reason: 'test evidence: _via_less_large_node_violations now sets capability=atom
    per finding, exercised by this file''s existing SYS107 fixture tests'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/strata/surface.md
  reason: 'MEASURED: the pre-existing frob:doc anchor on SYS107/_via_less_large_node_violations
    already points at docs/strata/surface.md#may-scope (set by T-1440/T-1451), not
    docs/strata/selfconform.md -- the ticket''s own declared doc file was the wrong
    one for this specific anchor'
  actor: logan
  at: '2026-08-16'
evidence:
- tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_sys107_fail_closed_atoms_are_always_error
- tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_sys107_net_via_less_still_defaults_to_warn
- tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_sys107_net_via_less_still_escalates_under_require_may_scope
- tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_sys107_no_capability_falls_back_to_config_gated_behavior
- tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_selfaudit_violation_escalates_sys107_exec_to_error
- tests/unit/strata/test_sys107_via_scope_advisory.py::TestViaLessLargeNodeAdvisory::test_via_less_grant_carries_the_offending_atom
- tests/unit/strata/test_sys107_via_scope_advisory.py::TestViaLessLargeNodeAdvisory::test_via_less_grants_on_two_atoms_fire_two_separate_findings
designated_repro_test: tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_selfaudit_violation_escalates_sys107_exec_to_error
threat: null
component: null
anchor: false
anchor_reason: null
---
Measured: SYS107 (T-1451, _selfconform.py) is the only check covering a via-less (whole-file/whole-node) grant, and its own docstring states it is 'Deliberately WARN, not ERROR' for every kind, including exec/eval/install-hook/ffi -- the kinds that let a node run attacker-influenced code or persist beyond itself. Today a node can carry an unbounded, ever-growing via-less exec/eval/install-hook/ffi grant indefinitely: nothing in frob check --only sys fails closed on it, so it never blocks a land. (SYS101 stale-design already prunes grants for capabilities that stop being observed, which is a genuinely separate and already-closed problem -- this ticket is only about via-less breadth on the fail-closed kinds, not staleness.) Acceptance: a positive-control test-only strata fixture (do not edit design/frob.strata's real declarations for this) with a node declaring a via-less may "exec" grant MUST be reported at ERROR severity by the selfconform check, not WARN; this test must FAIL against current main (SYS107 currently returns WARN for exactly this case) and pass after the fix. Scope the upgrade explicitly to exec/eval/install-hook/ffi -- do not touch net/fs.read/fs.write severity, which stay WARN-appropriate at this breadth per SYS107's existing rationale, to avoid mass unrelated churn across design/frob.strata's existing declarations. If any of design/frob.strata's REAL existing nodes already carries a via-less grant on one of these four kinds, narrowing it to via globs (or filing a follow-up per node if narrowing needs deeper investigation) is in scope as a consequence of turning the check to ERROR, and must not be silently waived to make the gate pass.