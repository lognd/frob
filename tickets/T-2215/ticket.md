---
id: T-2215
title: wire must_still_pass_violations (BUG003) into frob ticket land/close, mirroring
  BUG002
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
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
