---
id: T-1323
title: land wip snapshot committed out-of-scope frob:waive deletions (T-1234 land
  stripped 50 PERF waivers)
state: done
kind: incident
origin: agent
created: '2026-07-29'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_land_merge.py
- src/frob/gates/_fix_engine.py
- tests/test_ticket_land.py
- tests/test_gates.py
- docs/modules/gates.md
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/tickets/_models.py
- docs/modules/tickets.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: 'scope-closure warnings: fix_engine frob:doc targets live there'
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'pre-land Tier-A invocation site: the interim WAIVE004 exclusion lands here'
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/tickets/_models.py
  reason: T-1323 adds LandError.OutOfScopeWaiveDeletion and the out-of-scope frob:waive-deletion
    land refusal; both the enum's home module and its affects()-closure doc need to
    be in scope
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/modules/tickets.md
  reason: T-1323 adds LandError.OutOfScopeWaiveDeletion and the out-of-scope frob:waive-deletion
    land refusal; both the enum's home module and its affects()-closure doc need to
    be in scope
  actor: logan
  at: '2026-07-29'
- op: add
  glob: design/frob.strata
  reason: frob sys sync-interface's own generated fix for the two new public WAIVE004-guard
    test classes (SELFAUDIT001/SYS104) touches this file, same as land's own pre-land
    absorption step would
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_ticket_land.py::TestUncommittedWaiveDeletionRefusal::test_out_of_scope_undeclared_waive_deletion_refuses_before_merge
- tests/test_ticket_land.py::TestUncommittedWaiveDeletionRefusal::test_in_scope_waive_deletion_is_allowed
- tests/test_ticket_land.py::TestUncommittedWaiveDeletionRefusal::test_declared_in_done_report_waive_deletion_is_allowed
- tests/test_gates.py::TestWaive004DegradedRunGuard::test_native001_degraded_run_deletes_nothing
- tests/test_gates.py::TestWaive004DegradedRunGuard::test_skipped_stage_degraded_run_deletes_nothing
- tests/test_gates.py::TestWaive004DegradedRunGuard::test_mass_invalidation_of_one_rule_deletes_nothing
- tests/test_gates.py::TestWaive004DegradedRunGuard::test_healthy_run_below_threshold_still_deletes
designated_repro_test: null
reviews:
- verdict: reject
  reviewer: reviewer-agent (coordinator-relayed)
  findings: 'Declaration escape hatch over-permissive: substring match over the entire
    ticket body with OR semantics (file in body or rule in body). In an append-only
    ledger an incidental prose mention of a rule id counts as disclosure, laundering
    a waive deletion. Required fix: scope the search to the Done report section and
    require the (file, rule) pair together on one line. Fixed in rework commit; negative
    test added.'
  commit: 434839c7567470eeec460841872517a257d2eaff
  at: '2026-07-29'
acceptance:
- text: GIVEN a worktree with an uncommitted out-of-scope frob:waive deletion WHEN
    frob ticket land runs THEN the land refuses before merge with an error naming
    the file and deleted waiver
  evidence:
  - tests/test_ticket_land.py::TestUncommittedWaiveDeletionRefusal::test_out_of_scope_undeclared_waive_deletion_refuses_before_merge
  - tests/test_ticket_land.py::TestUncommittedWaiveDeletionRefusal::test_in_scope_waive_deletion_is_allowed
  - tests/test_ticket_land.py::TestUncommittedWaiveDeletionRefusal::test_declared_in_done_report_waive_deletion_is_allowed
- text: GIVEN fix_waive004_stale_waiver whose verification run_gates() executed with
    stale natives or a skipped stage THEN it deletes nothing
  evidence:
  - tests/test_gates.py::TestWaive004DegradedRunGuard::test_native001_degraded_run_deletes_nothing
  - tests/test_gates.py::TestWaive004DegradedRunGuard::test_skipped_stage_degraded_run_deletes_nothing
  - tests/test_gates.py::TestWaive004DegradedRunGuard::test_mass_invalidation_of_one_rule_deletes_nothing
  - tests/test_gates.py::TestWaive004DegradedRunGuard::test_healthy_run_below_threshold_still_deletes
- text: GIVEN the confirmed root cause of the 2026-07-29 stripping THEN the ticket's
    Done report names it with a reproducing test
  evidence:
  - tests/test_gates.py::TestWaive004DegradedRunGuard::test_mass_invalidation_of_one_rule_deletes_nothing
  - tests/test_gates.py::TestWaive004DegradedRunGuard::test_native001_degraded_run_deletes_nothing
threat: null
component: null
---
Incident 2026-07-29: the T-1234 land produced a pre-land wip snapshot
commit (6d4d7dc3 on worktree branch worktree-agent-a35b29166b3bc617a)
that captured uncommitted worktree state in which every single-line
`frob:waive PERF00x` comment had been stripped across 50 files. The
land commit 5e989183 carried those deletions onto main, regressing
gate:PERF from 0 errors to 42 (PERF is ERROR-tier since T-0972).
Neither the T-1227/T-1234 implementer nor the reviewer committed or
reported these edits; both reported a clean tree. Coordinator restored
the waivers on main in fa77749f (47 files via checkout of the land
parent, 3 hand re-inserts in files with legitimate sibling edits) and
verified gate:PERF back to 0 errors / 97 waived.

Root cause: UNKNOWN -- must be established, not assumed. Candidate
mechanisms to investigate, in order of plausibility:

1. `fix_waive004_stale_waiver` (T-1261, landed fa42ccf3 ~40 min before
   this land) mass-classifying waivers as stale because its
   self-manufactured full `run_gates()` verification ran DEGRADED in
   the worktree (stale/missing natives -> PERF reach analysis finds
   nothing -> every PERF waiver looks stale). The land merges main
   into the branch before its fresh checks, so the handler code WAS
   present in the worktree at land time even though the branch predates
   it. Establish what invoked it: does any land/check path reach
   `apply_tier_a_fixes` without an explicit `--fix`?
2. A config/default regression from T-1260's `--fix` plumbing
   (AppConfig bool default) turning fixes on for `frob check` runs the
   land performs post-merge.
3. Some other actor editing the worktree between review and land.

Guards to implement regardless of which mechanism is confirmed:

- `frob ticket land` must refuse (or hard-prompt) when the wip
  snapshot's delta touches files outside the landing ticket set's
  scope; at minimum, any `frob:waive` DELETION in the snapshot that no
  landing ticket declares is an ERROR-tier refusal. A land snapshot is
  supposed to preserve in-flight agent work, not launder unattributed
  repo-wide edits onto main.
- `fix_waive004_stale_waiver` must refuse to classify anything stale
  when its verification run is degraded: natives stale, a gate stage
  skipped/errored, or a stage reporting an anomalous zero-finding
  count vs the recorded baseline pool. Prefer prove-fresh-or-do-nothing.
- Regression test: a land whose worktree contains an uncommitted
  out-of-scope frob:waive deletion must fail with the new refusal.