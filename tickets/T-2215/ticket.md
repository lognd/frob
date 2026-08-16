---
id: T-2215
title: wire must_still_pass_violations (BUG003) into frob ticket land/close, mirroring
  BUG002
state: done
kind: feature
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/gates/_waive.py
- tests/unit/test_ticket_land_bug003_t2215.py
evidence_scope:
- tests/unit/test_ticket_land_bug003_t2215.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_land_bug003_t2215.py
  reason: T-2215's own regression test file for the BUG003 land/close wiring
  actor: logan
  at: '2026-08-16'
evidence:
- tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassWiring::test_land_refuses_when_control_broke_at_fix
- tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassWiring::test_land_succeeds_when_gate_reports_clean
- tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassWiring::test_waived_finding_is_suppressed_but_logged
- tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassWaiver::test_reason_present_suppresses
- tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassWaiver::test_bare_directive_without_reason_does_not_suppress
- tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassCombinesWithBug002::test_land_deferred_refuses_on_bug003_alone
- tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassCombinesWithBug002::test_land_synchronous_refuses_on_bug003_alone
- tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassCombinesWithBug002::test_close_refuses_on_bug003_alone
designated_repro_test: null
evidence_changes:
- old_node: tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassWiring::test_land_succeeds_when_no_directive
  new_node: tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassWiring::test_land_succeeds_when_gate_reports_clean
  reason: merged two near-duplicate tests into one parametrized test to resolve DUP002
  actor: logan
  at: '2026-08-16'
- old_node: tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassWiring::test_land_succeeds_when_control_passes_both
  new_node: tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassWiring::test_land_refuses_when_control_broke_at_fix
  reason: merged two near-duplicate tests into one parametrized test to resolve DUP002;
    this node id already appears earlier in the evidence list, dedup by rebinding
    to another already-bound real id
  actor: logan
  at: '2026-08-16'
threat: null
component: null
anchor: false
anchor_reason: null
---
Follow-up to T-2193 (filed while working it; T-2193's own declared scope
is src/frob/gates/_mutation_evidence.py alone, plus its doc/test files --
no CLI/model/land-pipeline changes).

T-2193 added `must_still_pass_violations` (BUG003) to
src/frob/gates/_mutation_evidence.py: given a `frob:must-still-pass
NODE-ID` directive in a ticket's body, it runs the same node id against
both the ticket's fix and its parent commit and refuses if the
capability the directive names either fails at the fix (broke) or never
passed at the parent (a misconfigured designation). See
docs/modules/tickets-landing.md#bug003-the-positive-direction-must-still-pass-control-t-2193
for the full mechanism and rationale (three measured instances --
T-2156, T-2177, `frob cycle` -- where BUG002/TEST016 both passed while
the underlying capability was silently disabled).

The function is implemented and unit-tested (11 tests in
tests/test_gates_mutation_evidence.py, including one real end-to-end
repro with no mocking) but has ZERO callers: it is not wired into
`frob.tickets._land`'s land-time precheck, nor into
`frob.app.ticket_runner`'s direct `frob ticket close` CLI path, the way
BUG002/TEST016 both are (`mutation_evidence_violations`/
`bug_repro_violations`'s own module docstring names these two call
sites). Right now `frob:must-still-pass NODE-ID` in a ticket body is
inert prose -- nothing runs the check.

Scope for this follow-up: wire `must_still_pass_violations` into the
same two call sites BUG002 already uses
(`frob.tickets._land._check_mutation_evidence` or its sibling, and
`frob.app.ticket_runner`'s close path) with the same severity posture
(always ERROR when it fires, per BUG002's own precedent) and the same
escape-hatch shape (a `frob:waive BUG003 reason="..."` body-text
override, mirroring `_BUG002_WAIVER_RE`). Also worth deciding at that
point: should `--designate-repro`-style validate-at-designate-time
checking apply to the `frob:must-still-pass` directive too (T-1929's
`bug_repro_outcome_at_ref` precedent), or is land/close-time-only
sufficient for a first landing. Likely scope: src/frob/tickets/_land.py,
src/frob/app/ticket_runner/_close_cmd.py (or wherever BUG002's close
path lives), possibly src/frob/gates/_waive.py's known-rule registry if
`frob:waive BUG003` should route through the shared WAIVE002/003
validation machinery rather than staying a bespoke body-text regex like
BUG002's own waiver.