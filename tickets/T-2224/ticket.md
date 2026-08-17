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
land_commit: null
---
Measured: SYS107 (T-1451, _selfconform.py) is the only check covering a via-less (whole-file/whole-node) grant, and its own docstring states it is 'Deliberately WARN, not ERROR' for every kind, including exec/eval/install-hook/ffi -- the kinds that let a node run attacker-influenced code or persist beyond itself. Today a node can carry an unbounded, ever-growing via-less exec/eval/install-hook/ffi grant indefinitely: nothing in frob check --only sys fails closed on it, so it never blocks a land. (SYS101 stale-design already prunes grants for capabilities that stop being observed, which is a genuinely separate and already-closed problem -- this ticket is only about via-less breadth on the fail-closed kinds, not staleness.) Acceptance: a positive-control test-only strata fixture (do not edit design/frob.strata's real declarations for this) with a node declaring a via-less may "exec" grant MUST be reported at ERROR severity by the selfconform check, not WARN; this test must FAIL against current main (SYS107 currently returns WARN for exactly this case) and pass after the fix. Scope the upgrade explicitly to exec/eval/install-hook/ffi -- do not touch net/fs.read/fs.write severity, which stay WARN-appropriate at this breadth per SYS107's existing rationale, to avoid mass unrelated churn across design/frob.strata's existing declarations. If any of design/frob.strata's REAL existing nodes already carries a via-less grant on one of these four kinds, narrowing it to via globs (or filing a follow-up per node if narrowing needs deeper investigation) is in scope as a consequence of turning the check to ERROR, and must not be silently waived to make the gate pass.

## Done report

Threat closed: an unbounded, ever-growing via-less exec/eval/
install-hook/ffi grant on a large node could persist indefinitely
with nothing in `frob check --only sys` failing closed on it. These
four kinds let a node run attacker-influenced code (exec/eval),
persist beyond itself (install-hook), or cross the language-runtime
trust boundary (ffi) -- exactly the shape SYS107 (T-1451) already
detects but only ever WARNs on, opt-in-escalatable only via
`[strata] require_may_scope`, which a repo owner could simply never
set.

Root cause, measured (not guessed): `_selfaudit_severity` (src/frob/
gates/_sys_selfaudit.py) was the ONLY place deciding SYS107's WARN vs
ERROR severity, keyed purely on the sub_rule name -- no per-capability
distinction existed anywhere. `_via_less_large_node_violations`
(src/frob/strata/_selfconform.py) fired ONE finding per offending
NODE, not per grant, so even if severity had been capability-aware,
there was no per-atom field to key off (SelfConformViolation.
capability was never set for a SYS107 finding).

Fix, scoped narrowly to exec/eval/install-hook/ffi as instructed:
- _via_less_large_node_violations now emits one finding PER via-less
  ATOM (SYS107_FAIL_CLOSED_ATOMS marks the four fail-closed kinds),
  setting capability=atom on each -- the same multi-instance shape
  SYS100/SYS101 already use. A node with via-less grants on BOTH a
  fail-closed and a non-fail-closed atom now produces one ERROR and
  one WARN finding, not one WARN finding covering both (confirmed by
  test_via_less_grants_on_two_atoms_fire_two_separate_findings).
- _selfaudit_severity threads that capability through: a fail-closed
  atom is ALWAYS Severity.ERROR, no require_may_scope opt-in needed.
  net/fs.read/fs.write and every other capability kind are completely
  untouched -- they keep the exact original WARN-unless-require_may_
  scope posture (confirmed by test_sys107_net_via_less_still_
  defaults_to_warn and test_sys107_net_via_less_still_escalates_
  under_require_may_scope, both must-still-pass controls).

Real design/frob.strata check: walked every node in the live model
directly (bind_code + _node_real_code_file_count against the real
design) BEFORE writing this fix -- zero real nodes currently carry a
via-less grant on exec/eval/install-hook/ffi at large-node breadth, so
nothing needed narrowing as a consequence of turning this check to
ERROR.

Repro: test_selfaudit_violation_escalates_sys107_exec_to_error
committed alone at 7a5dbc4d6 (alongside 6 sibling repro/control
tests), confirmed FAILED_AT_PARENT via `frob ticket evidence
--check-repro ... --base-ref 7a5dbc4d6`. Fix committed separately at
45b48f923; doc/gate follow-up at f7055a397.

Tests: 27 passed across tests/unit/gates/test_sys_selfaudit.py,
tests/unit/strata/test_sys107_via_scope_advisory.py, and
tests/test_gates.py::TestSelfAuditGate (the last is the pre-existing
SELFAUDIT001 gate integration suite, run unchanged as a must-still-
pass control -- all 12 pass, confirming the capability= kwarg change
did not disturb the existing gate wiring).

`frob check --ticket T-2224`: 0 errors attributable to
src/frob/strata/_selfconform.py, src/frob/gates/_sys_selfaudit.py,
tests/unit/gates/test_sys_selfaudit.py, tests/unit/strata/
test_sys107_via_scope_advisory.py, docs/strata/surface.md, or
design/frob.strata (checked directly against the JSON diagnostics for
each path). 36 pre-existing repo-wide errors remain, none in these
files.

Scope widened beyond the declared three files, each with a measured
reason recorded via frob ticket scope: src/frob/gates/_sys_selfaudit.py
(the ONLY place SYS107 severity is decided -- _selfconform.py itself
carries no severity concept at all), tests/unit/gates/
test_sys_selfaudit.py and tests/unit/strata/
test_sys107_via_scope_advisory.py (test evidence), and
docs/strata/surface.md (the pre-existing frob:doc anchor for this
section -- the ticket's own declared docs/strata/selfconform.md was
the wrong file for it).

### Changed
```
 docs/strata/surface.md                             |  26 +++--
 src/frob/gates/_sys_selfaudit.py                   |  57 ++++++++---
 src/frob/strata/_selfconform.py                    | 110 +++++++++++++++------
 tests/unit/gates/test_sys_selfaudit.py             |  67 +++++++++++++
 .../unit/strata/test_sys107_via_scope_advisory.py  |  55 +++++++++++
 tickets/T-2224/ticket.md                           |  45 ++++++++-
 6 files changed, 310 insertions(+), 50 deletions(-)
```

### Evidence
- `tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_sys107_fail_closed_atoms_are_always_error` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_sys107_net_via_less_still_defaults_to_warn` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_sys107_net_via_less_still_escalates_under_require_may_scope` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_sys107_no_capability_falls_back_to_config_gated_behavior` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_selfaudit_violation_escalates_sys107_exec_to_error` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sys107_via_scope_advisory.py::TestViaLessLargeNodeAdvisory::test_via_less_grant_carries_the_offending_atom` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sys107_via_scope_advisory.py::TestViaLessLargeNodeAdvisory::test_via_less_grants_on_two_atoms_fire_two_separate_findings` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2224/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2224/tests/test_ticket_work_and_land_finish.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
