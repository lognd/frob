---
id: T-2400
title: TICK006 auto-files false phantom-citation tickets for ids that exist on main
  but postdate the worktree
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine.py
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_gates.py
- tests/test_ticket_work_and_land_finish.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: 'TICK006 phantom-citation false positive: resolve known ids against the
    land merge target, not just the worktree/archive'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'TICK006 phantom-citation false positive: resolve known ids against the
    land merge target, not just the worktree/archive'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_gates.py
  reason: 'TICK006 phantom-citation false positive: resolve known ids against the
    land merge target, not just the worktree/archive'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: 'TICK006 phantom-citation false positive: resolve known ids against the
    land merge target, not just the worktree/archive'
  actor: logan
  at: '2026-08-18'
triage_changes:
- field: priority
  old_value: high
  new_value: critical
  reason: 'THIRD occurrence in a single day, confirming this is routine rather than
    incidental: T-2382/T-2383 (Series U land of T-2341), T-2398/T-2399 (Series Y land
    of T-2386), T-2404 (Series W land of T-2380). Six spurious ticket ids burned,
    three separate agents forced into a verify-then-drop detour mid-land. Escalated
    on frequency plus blast radius: drops are TERMINAL here (no undrop), so a filer
    that cries wolf three times a day is one careless agent away from destroying a
    real finding.'
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_gates.py::TestFixEngineTierA::test_tick006_id_on_merge_target_but_not_worktree_is_silent
- tests/test_gates.py::TestFixEngineTierA::test_tick006_genuinely_nonexistent_id_still_fires_with_merge_target
- tests/test_gates.py::TestFixEngineTierA::test_tick006_not_measured_merge_target_files_nothing
- tests/test_ticket_work_and_land_finish.py::TestResolveMergeTargetKnownIds::test_measured_unions_active_and_archived_ids
- tests/test_ticket_work_and_land_finish.py::TestResolveMergeTargetKnownIds::test_unloadable_active_ledger_is_not_measured
- tests/test_ticket_work_and_land_finish.py::TestResolveMergeTargetKnownIds::test_unloadable_archive_is_not_measured
designated_repro_test: null
acceptance:
- text: Given a Done report citing a ticket that exists on main but was filed after
    the landing worktree was cut, when the land's TICK006 check runs, then it files
    no recovery ticket.
  evidence:
  - tests/test_gates.py::TestFixEngineTierA::test_tick006_id_on_merge_target_but_not_worktree_is_silent
  - tests/test_gates.py::TestFixEngineTierA::test_tick006_genuinely_nonexistent_id_still_fires_with_merge_target
  - tests/test_gates.py::TestFixEngineTierA::test_tick006_not_measured_merge_target_files_nothing
  - tests/test_ticket_work_and_land_finish.py::TestResolveMergeTargetKnownIds::test_measured_unions_active_and_archived_ids
  - tests/test_ticket_work_and_land_finish.py::TestResolveMergeTargetKnownIds::test_unloadable_active_ledger_is_not_measured
  - tests/test_ticket_work_and_land_finish.py::TestResolveMergeTargetKnownIds::test_unloadable_archive_is_not_measured
- text: Given a Done report citing a genuinely nonexistent ticket id, when the same
    check runs, then it still files a recovery ticket, proving the fix did not simply
    disable the check.
  evidence:
  - tests/test_gates.py::TestFixEngineTierA::test_tick006_id_on_merge_target_but_not_worktree_is_silent
  - tests/test_gates.py::TestFixEngineTierA::test_tick006_genuinely_nonexistent_id_still_fires_with_merge_target
  - tests/test_gates.py::TestFixEngineTierA::test_tick006_not_measured_merge_target_files_nothing
  - tests/test_ticket_work_and_land_finish.py::TestResolveMergeTargetKnownIds::test_measured_unions_active_and_archived_ids
  - tests/test_ticket_work_and_land_finish.py::TestResolveMergeTargetKnownIds::test_unloadable_active_ledger_is_not_measured
  - tests/test_ticket_work_and_land_finish.py::TestResolveMergeTargetKnownIds::test_unloadable_archive_is_not_measured
- text: Given the check cannot read the merge target's ledger, when it runs, then
    it reports NOT_MEASURED with a reason rather than concluding the citation is phantom.
  evidence:
  - tests/test_gates.py::TestFixEngineTierA::test_tick006_id_on_merge_target_but_not_worktree_is_silent
  - tests/test_gates.py::TestFixEngineTierA::test_tick006_genuinely_nonexistent_id_still_fires_with_merge_target
  - tests/test_gates.py::TestFixEngineTierA::test_tick006_not_measured_merge_target_files_nothing
  - tests/test_ticket_work_and_land_finish.py::TestResolveMergeTargetKnownIds::test_measured_unions_active_and_archived_ids
  - tests/test_ticket_work_and_land_finish.py::TestResolveMergeTargetKnownIds::test_unloadable_active_ledger_is_not_measured
  - tests/test_ticket_work_and_land_finish.py::TestResolveMergeTargetKnownIds::test_unloadable_archive_is_not_measured
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
TWICE TODAY, a Tier-A `TICK006` auto-fix during land filed spurious
"phantom citation recovery" tickets for ticket ids that GENUINELY EXIST
on main, forcing the landing agent to hand-drop them:

  - Series U's land of T-2341 auto-filed T-2382/T-2383 citing T-2366 and
    T-2367. Both cited tickets were real (`frob ticket show` confirmed);
    the agent verified and dropped the two spurious ones.
  - Series Y's land of T-2386 auto-filed T-2398/T-2399 citing T-2388 and
    T-2389. Both cited tickets were real, filed BEFORE the worktree was
    cut; the agent verified and dropped both.

MECHANISM (from the second occurrence, which pins it down). The Done
report cites ticket ids that exist on MAIN but were created after the
agent's WORKTREE was cut. The phantom check evidently resolves the
citation against the worktree's own view of the ledger rather than
against main, so a ticket filed by the coordinator or a sibling agent
mid-flight looks nonexistent from inside the worktree. It is not a
missing ticket -- it is a stale view of the ticket set.

This is the same root cause class as T-2350/T-2351 (already fixed for a
different shape) and belongs to the family of auto-filer defects that
have now produced FOUR distinct kinds of malformed record: absolute
paths in a scope field (T-2342, which bricked `frob ticket new`
fleet-wide), identity-less quarantine findings (T-2207), stale-baseline
"new" identities (pre-existing findings filed as new), and now
false-phantom citations.

COST. Each occurrence burns two ticket ids, forces the landing agent
into a verify-then-drop detour at the most expensive moment (mid-land),
and -- worse -- trains agents to treat auto-filed tickets as
presumptively bogus. A recovery mechanism that cries wolf is worse than
none, because the one time it is right it will also be dropped. Drops
are TERMINAL in this repo (no undrop), so a false-positive filer is one
careless agent away from destroying a real finding.

FIX SHAPE. Resolve a cited ticket id against the ledger as it exists on
the MERGE TARGET (main), not the worktree's snapshot -- the citation is
being checked for a land onto main, so main is the correct reference.
Where that is genuinely unavailable, the check must report NOT_MEASURED
rather than concluding "phantom" (epic T-2391): concluding absence from
an incomplete view is precisely the silent-wrong-answer class that
doctrine exists to eliminate. Filing a recovery ticket must be the
action of LAST resort, taken only when the id is provably absent from
the merge target.

Positive control both ways is mandatory here, because a lazy fix
(suppress phantom filing entirely) would pass a one-sided test:
  - must-still-fire: a Done report citing a genuinely nonexistent
    ticket id must still produce a recovery filing;
  - must-now-be-silent: a Done report citing a ticket that exists on
    main but postdates the worktree's cut must file nothing.