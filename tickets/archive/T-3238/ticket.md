---
id: T-3238
title: 'post-land sweep regression from T-3220: 1 new (rule, file) identit(ies), 2
  finding(s) (DRIFT002)'
state: done
kind: bug
origin: agent
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/clean/_core.py
- tests/test_clean.py
findings:
- - DRIFT002
  - src/frob/clean/_core.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_clean.py
  reason: DRIFT002's own remedy for a dangling frob:tests reference with no rename
    candidates is to write the missing test -- doing so is this ticket's direct fix,
    not unrelated scope creep
  actor: logan
  at: '2026-08-28'
evidence:
- tests/test_clean.py::test_deep_clean_preserves_rapid_debt_jsonl
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 83bfe533a80f908ba8701da6d0a2395658a53e05
---
The deferred post-land unscoped sweep (T-1684) for T-3220 at commit c5ea05d6947c0c69d6ef31d6b80bbee987259f39 found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 2 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- DRIFT002  src/frob/clean/_core.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DRIFT002  src/frob/clean/_core.py  -> attributed to T-3220 (commit c5ea05d6947c, already closed/dropped -- filed below) via src/frob/clean/_core.py::_match_candidates

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.