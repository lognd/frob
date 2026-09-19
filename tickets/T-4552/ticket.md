---
id: T-4552
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-4548):
  1 new (rule, file) identit(ies), 1 finding(s) (TICK010)'
state: done
kind: bug
origin: agent
created: '2026-09-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .git/frob-leases/T-4550.json
- src/frob/tickets/_land_git_ops.py
- tests/unit/test_land_merge_conflict_drop.py
- docs/modules/tickets-landing.md
findings:
- - TICK010
  - /home/logan/projects/frob/.git/frob-leases/T-4550.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: 'COV002: T-4498 helpers need frob:ticket/frob:tests edges'
  actor: logan
  at: '2026-09-17'
- op: add
  glob: tests/unit/test_land_merge_conflict_drop.py
  reason: 'DUP001: extract shared helper for near-identical test blocks'
  actor: logan
  at: '2026-09-17'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: 'DOC006: pointer does not resolve, fix or waive'
  actor: logan
  at: '2026-09-17'
body_changes:
- mode: append
  reason: kind=bug BUG002 requires a repro test that fails at parent, but this ticket
    has no runtime behaviour defect to repro -- pure gate-metadata residue
  actor: logan
  at: '2026-09-17'
  old_length: 1254
  new_length: 2131
evidence:
- tests/unit/test_land_merge_conflict_drop.py::TestCapabilityRatchetConflictRefused::test_conflicting_strata_via_list_refuses_instead_of_dropping
- tests/unit/test_land_merge_conflict_drop.py::TestCapabilityRatchetConflictRefused::test_conflicting_ratchet_lock_refuses_instead_of_dropping
designated_repro_test: null
acceptance:
- text: TICK010 finding on .git/frob-leases/T-4550.json is confirmed stale (T-4550's
    worktree holder is dead and the lease is for a different, unrelated ticket) --
    no code fix required, documented as such
  evidence:
  - tests/unit/test_land_merge_conflict_drop.py::TestCapabilityRatchetConflictRefused::test_conflicting_ratchet_lock_refuses_instead_of_dropping
- text: 'COV002 on _land_git_ops.py''s T-4498 merge-conflict helpers resolved: frob:ticket
    edges retargeted to T-4552 (T-4498 is done) and frob:tests edges added for _land_ticket_for_commit_touching,
    _resolve_one_out_of_scope_conflict, _log_capability_ratchet_refusal'
  evidence:
  - tests/unit/test_land_merge_conflict_drop.py::TestCapabilityRatchetConflictRefused::test_conflicting_strata_via_list_refuses_instead_of_dropping
  - tests/unit/test_land_merge_conflict_drop.py::TestCapabilityRatchetConflictRefused::test_conflicting_ratchet_lock_refuses_instead_of_dropping
- text: 'DUP001 on tests/unit/test_land_merge_conflict_drop.py resolved: shared _seed_widget_worktree
    helper extracted from the two near-identical test bodies'
  evidence:
  - tests/unit/test_land_merge_conflict_drop.py::TestCapabilityRatchetConflictRefused::test_conflicting_strata_via_list_refuses_instead_of_dropping
- text: 'DOC006 on docs/modules/tickets-landing.md resolved: the split frob:waive-DOC006-comment/backtick-span
    around ''frob sys sync-interface'' repaired so the pointer resolves as a single
    recognized inline-code span'
  evidence:
  - tests/unit/test_land_merge_conflict_drop.py::TestCapabilityRatchetConflictRefused::test_conflicting_strata_via_list_refuses_instead_of_dropping
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-4548) at commit 33bfb966753a82da4cdae49e5768de1c3784b91c found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4550.json

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4550.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

frob:waive BUG002 reason="gate-metadata residue, no runtime behaviour to repro"

This ticket's finding (a stale TICK010 lease-lifecycle warning on a leftover lease file, plus COV002/DUP001/DOC006 gate-metadata residue disposed onto it) is not a runtime defect with an observable failure mode -- there is no code path whose behavior changed and no repro is constructible against the parent commit. The TICK010 finding itself is confirmed stale: T-4550's worktree holder is dead and the referenced lease belongs to an unrelated ticket, not to any code this ticket touched. Fixed instead: the frob:ticket/frob:tests edges on T-4498's now-closed-ticket-pointing directives (COV002), a DUP001 test-code duplication (extracted shared helper), and a DOC006 doc-pointer split across an inline HTML waive comment in docs/modules/tickets-landing.md. None of these are behavior changes.