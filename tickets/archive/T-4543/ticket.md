---
id: T-4543
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-3613):
  2 new (rule, file) identit(ies), 12 finding(s) (COV002, TICK010)'
state: done
kind: bug
origin: agent
created: '2026-09-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .git/frob-leases/T-4511.json
- src/frob/dup/_legacy_cs.py
- tests/unit/test_ticket_runner_land_cmd_flags.py
findings:
- - COV002
  - src/frob/dup/_legacy_cs.py
- - TICK010
  - /home/logan/projects/frob/.git/frob-leases/T-4511.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_runner_land_cmd_flags.py
  reason: fix ty invalid-argument-type per T-4543 finding
  actor: logan
  at: '2026-09-16'
body_changes:
- mode: append
  reason: BUG002 waiver for gate-metadata residue (coordinator)
  actor: logan
  at: '2026-09-17'
  old_length: 1897
  new_length: 2167
evidence:
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandDrain::test_two_entries_call_land_core_per_entry_with_its_own_ticket_id
- tests/unit/test_support_csharp.py::TestCsharpDupFacetFires::test_find_duplicates_reports_near_duplicate_methods
designated_repro_test: null
acceptance:
- text: ty invalid-argument-type in tests/unit/test_ticket_runner_land_cmd_flags.py
    is fixed (dict typed dict[str, Any], model built via QueueEntry.model_validate)
  evidence:
  - tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandDrain::test_two_entries_call_land_core_per_entry_with_its_own_ticket_id
- text: COV002 on src/frob/dup/_legacy_cs.py is resolved by adding frob:ticket T-4543
    edges to every changed public symbol
  evidence:
  - tests/unit/test_support_csharp.py::TestCsharpDupFacetFires::test_find_duplicates_reports_near_duplicate_methods
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-3613) at commit 42bbe4c2bf478b00791859fab6f1fa7fc4d706da found 3 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 12 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- COV002  src/frob/dup/_legacy_cs.py
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4511.json

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV002  src/frob/dup/_legacy_cs.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4511.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- invalid-argument-type  tests/unit/test_ticket_runner_land_cmd_flags.py  -> attributed to T-3613 (commit 42bbe4c2bf47, already closed/dropped -- filed below) via tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandDrain.test_two_entries_call_land_core_per_entry_with_its_own_ticket_id -> src/frob/app/ticket_runner/_land_cmd.py::_print_land_proof -> src/frob/app/ticket_runner/_land_cmd.py::_land -> src/frob/app/ticket_runner/_land_cmd.py::_apply_land_default_queue

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

frob:waive BUG002 reason="post-land sweep residue: the defect is frob check GATE state (a ty invalid-argument-type on a test helper and COV002 directive coverage on src/frob/dup/_legacy_cs.py), not application behaviour a pytest repro can fail on at the parent commit"