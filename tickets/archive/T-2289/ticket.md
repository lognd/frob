---
id: T-2289
title: 'T-1914 sibling-state-regression guard names the LANDING ticket as its own
  sibling: 6 of 6 refusals were self-conflicts, 40% of all land attempts'
state: done
kind: bug
origin: agent
created: '2026-08-17'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_land_git_ops.py
- src/frob/tickets/_store.py
- tests/unit/test_land_sibling_regression.py
- docs/modules/tickets-landing.md
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land.py
  reason: narrow to the T-1914 sibling-guard/self-conflict merge machinery and its
    regression test
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: narrow to the T-1914 sibling-guard/self-conflict merge machinery and its
    regression test
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/tickets/_store.py
  reason: narrow to the T-1914 sibling-guard/self-conflict merge machinery and its
    regression test
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/unit/test_land_sibling_regression.py
  reason: narrow to the T-1914 sibling-guard/self-conflict merge machinery and its
    regression test
  actor: logan
  at: '2026-08-17'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: doc closure target for _land.py's frob:doc anchors
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/test_ticket_land.py
  reason: T-2289's fix changes this file's own AC3 same-ticket-conflict test expectation
    (self-conflicts now auto-resolve instead of surfacing loudly)
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/test_land_sibling_regression.py::TestSelfConflictAutoResolve::test_genuine_sibling_conflict_still_refuses
- tests/unit/test_land_sibling_regression.py::TestSiblingStateRegressionGuard::test_regressed_sibling_is_detected_by_rank_comparison
- tests/unit/test_land_sibling_regression.py::TestSiblingStateRegressionGuard::test_no_regression_when_sibling_state_only_improves_or_holds
- tests/unit/test_land_sibling_regression.py::TestSiblingStateRegressionGuard::test_pre_fix_shape_would_have_silently_reverted_sibling
- tests/test_ticket_land.py::TestLedgerV2LandMergeStory::test_same_ticket_conflict_surfaces_loudly_no_splice
- tests/unit/test_land_sibling_regression.py::TestSelfConflictAutoResolve::test_self_conflict_lands_by_keeping_newer_state
designated_repro_test: tests/unit/test_land_sibling_regression.py::TestSelfConflictAutoResolve::test_self_conflict_lands_by_keeping_newer_state
acceptance:
- text: given a land whose only divergent ledger row is the landing ticket's own,
    when frob ticket land runs, then it resolves by keeping the newer state and does
    not refuse
  evidence:
  - tests/unit/test_land_sibling_regression.py::TestSelfConflictAutoResolve::test_self_conflict_lands_by_keeping_newer_state
- text: given a land where a genuine sibling ticket's row would regress, when frob
    ticket land runs, then it still refuses (guard not weakened)
  evidence:
  - tests/unit/test_land_sibling_regression.py::TestSelfConflictAutoResolve::test_genuine_sibling_conflict_still_refuses
  - tests/unit/test_land_sibling_regression.py::TestSiblingStateRegressionGuard::test_regressed_sibling_is_detected_by_rank_comparison
- text: given the regression tests, when they run, then both the self-conflict and
    genuine-sibling cases are covered as distinct must-pass/must-fail fixtures
  evidence:
  - tests/unit/test_land_sibling_regression.py::TestSelfConflictAutoResolve::test_self_conflict_lands_by_keeping_newer_state
  - tests/unit/test_land_sibling_regression.py::TestSelfConflictAutoResolve::test_genuine_sibling_conflict_still_refuses
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: 7788a1830a6201b7ec88020e983a79a79179cf5a
---
MEASURED 2026-08-17 by aggregating all 5 concurrent implementer agents'
Bash transcripts (288 tool calls, 6440s of command wall time).

T-1914's sibling-state-regression guard refused 6 land invocations. In
ALL 6, the "sibling" it named was the ticket being landed itself:

  landing T-2276 -> "regress sibling ticket(s) T-2276"
  landing T-2276 -> "regress sibling ticket(s) T-2276"
  landing T-2269 -> "regress sibling ticket(s) T-2269"
  landing T-2116 -> "regress sibling ticket(s) T-2116"
  landing T-2116 -> "regress sibling ticket(s) T-2116"
  landing T-2112 -> "regress sibling ticket(s) T-2112"

6 of 6 self-named, across 4 distinct tickets and 4 distinct agents. Not a
fluke.

IMPACT: land invocations = 15, of which 7 were refused (47%). This guard
alone accounts for 6 of those 7. Each refusal costs a ~100-150s land
attempt plus an agent turn spent hand-resolving a ledger conflict the
playbook (section 10) tells it to resolve by "keep the newer state" -- a
rule that is mechanical when the only ticket involved is the one being
landed.

MECHANISM (hypothesis, implementer to confirm): main advances the landing
ticket's OWN ledger row while the agent works (the start transition, an
evidence row, a rapid-sweep close-debt row). The worktree then holds an
older-or-divergent copy of that same row. The guard compares the merge
result against main per ticket id and sees the landing ticket's row moving
backwards -- correctly detecting divergence, but wrongly classifying it as
a SIBLING regression. A ticket is not its own sibling.

FIX DIRECTION: exclude the landing ticket id from the sibling set, and
resolve its own row by the playbook's existing keep-the-newer-state rule
automatically. The guard must still refuse for genuine siblings -- that is
the T-1914 behaviour worth keeping.

POSITIVE CONTROL REQUIRED: (1) a must-still-fail case where a GENUINE
sibling's row would regress -> still refused; (2) a must-now-pass case
where only the landing ticket's own row diverges -> lands without hand
resolution. A fix that merely narrows until the observed 6 disappear,
without case (1), is unsound -- an exemption matching the normal case
disables the guard.