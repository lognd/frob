---
id: T-2520
title: 'post-land sweep regression from T-2507: 1 new (rule, file) identit(ies), 0
  finding(s) (WIRE001)'
state: done
kind: bug
origin: agent
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/graph/summary.py
evidence_scope:
- tests/unit/gates/test_wire001_cli_dest_semantic.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): T-2520 is a T-1684 rapid post-land sweep filing
    against T-2507 (commit 1b91e2f2), claiming 1 new (rule,file) identity WIRE001
    src/frob/graph/summary.py -- but the ticket''s own body already discloses an independent
    re-measurement found 0 actual findings, and attribution came back UNATTRIBUTED
    (no candidate commits). Re-verified today (2026-08-18) against current main: unscoped
    frob check --json with gate-summary present, gate:WIRE family ran, 0 WIRE001 diagnostics
    anywhere in the run, none against src/frob/graph/summary.py or any other file.
    This matches the documented stale-baseline-reports-pre-existing-as-new false-positive
    class this ticket class is known for -- no code fix is applicable because there
    is no live finding to fix. Closing with no behavior change; WIRE001''s own test
    suite (test_wire001_cli_dest_semantic.py) still passes, cited as evidence that
    the gate itself is intact.'
  actor: logan
  at: '2026-08-18'
  old_length: 1154
  new_length: 2086
evidence:
- tests/unit/gates/test_wire001_cli_dest_semantic.py::TestWire001CliDestViolations::test_dest_wired_only_through_tuple_structure_is_not_flagged
- tests/unit/gates/test_wire001_cli_dest_semantic.py::TestWire001CliDestViolations::test_dest_mentioned_only_in_a_comment_is_flagged
- tests/unit/gates/test_wire001_cli_dest_semantic.py::TestWire001CliDestViolations::test_dest_not_wired_at_all_is_flagged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-2507 at commit 1b91e2f234e73f9fd9c7bd1b279949f5dcec83fd found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 0 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- WIRE001  src/frob/graph/summary.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- WIRE001  src/frob/graph/summary.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

frob:no-behavior-change reason="T-2520 is a T-1684 rapid post-land sweep filing against T-2507 (commit 1b91e2f2), claiming 1 new (rule,file) identity WIRE001 src/frob/graph/summary.py -- but the ticket's own body already discloses an independent re-measurement found 0 actual findings, and attribution came back UNATTRIBUTED (no candidate commits). Re-verified today (2026-08-18) against current main: unscoped frob check --json with gate-summary present, gate:WIRE family ran, 0 WIRE001 diagnostics anywhere in the run, none against src/frob/graph/summary.py or any other file. This matches the documented stale-baseline-reports-pre-existing-as-new false-positive class this ticket class is known for -- no code fix is applicable because there is no live finding to fix. Closing with no behavior change; WIRE001's own test suite (test_wire001_cli_dest_semantic.py) still passes, cited as evidence that the gate itself is intact."