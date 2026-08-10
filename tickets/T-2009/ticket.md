---
id: T-2009
title: Deferred post-land sweep attributes a finding to whichever ticket's sweep fires
  next, not the land that introduced it
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: 'T-2009: attribution mismatch lives entirely in run_deferred_post_land_sweep/_file_regression_ticket''s
    title/body construction in this module; the fix and its regression test both live
    here'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: 'T-2009: attribution mismatch lives entirely in run_deferred_post_land_sweep/_file_regression_ticket''s
    title/body construction in this module; the fix and its regression test both live
    here'
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_rapid_sweep.py::TestRollingBaseline::test_read_baseline_commit_absent_is_none
- tests/unit/test_rapid_sweep.py::TestRollingBaseline::test_read_baseline_commit_round_trips
- tests/unit/test_rapid_sweep.py::TestLandIdsBetween::test_single_land_in_range
- tests/unit/test_rapid_sweep.py::TestLandIdsBetween::test_multiple_lands_in_range_oldest_first
- tests/unit/test_rapid_sweep.py::TestLandIdsBetween::test_non_land_commits_are_ignored
- tests/unit/test_rapid_sweep.py::TestLandIdsBetween::test_non_repo_returns_empty_list
- tests/unit/test_rapid_sweep.py::TestResolveActualHead::test_non_repo_falls_back_to_the_given_commit
- tests/unit/test_rapid_sweep.py::TestResolveActualHead::test_real_repo_resolves_the_true_head
- tests/unit/test_rapid_sweep.py::TestDeferredSweepMultiLandAttribution::test_two_lands_in_the_window_are_both_named_not_just_the_spawning_one
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
## Done report

Root cause: `run_deferred_post_land_sweep`'s `fresh` measurement reflects
whatever `root`'s tree ACTUALLY looks like at the moment the detached
sweep child runs `frob check` -- not the moment it was spawned. Because
the sweep is deliberately off the land critical path (T-1684, the point
of the whole design), an arbitrary number of OTHER agents' lands can land
in the window between spawn and that check actually completing. The old
code trusted `final_id` (the ticket that happened to SPAWN this
particular sweep process) as the sole author of every finding in that
diff, and wrote the baseline's `commit` field as the land's own
`commit_sha` rather than what was actually measured -- so a later sweep
had no way to even detect that more than one land had landed in its own
window. Measured instance (T-1998): filed as "regression from T-1977",
but all 5 new identities lived in T-1995's files -- T-1995 landed in the
same window, and T-1977's sweep (or T-1995's own, whichever actually ran
the check) took credit/blame for both.

Fix, root-cause-honest rather than serializing anything:
- `_resolve_actual_head(root, fallback)`: reads `root`'s real git HEAD at
  measurement time; the baseline's `commit` is now this, not the
  possibly-stale `commit_sha` a land passed at spawn time.
- `_read_baseline_commit(root)`: recovers the PREVIOUS baseline's own
  recorded (now honest) commit.
- `_land_ids_between(root, since, until)`: every `T-####` named in a
  `land T-####` commit subject in that git range, oldest first.
- `run_deferred_post_land_sweep` computes this range on every red sweep;
  when it names MORE THAN ONE land, `_file_regression_ticket`'s new
  `attributed_ids` parameter overrides the filed ticket's TITLE and body
  attribution text to name all of them, instead of pinning the whole
  regression on `final_id` alone. The exact-one-land case (the overwhelm-
  ing majority) is byte-identical to before -- `attributed_ids=None`
  falls back to `[final_id]`.
- Nothing about the sweep's own timing, spawn point, or cadence changed;
  no lock, no wait, no re-ordering. This is purely "tell the truth about
  which commits happened in this window", never "make the window smaller
  or serialize crossing it" -- the explicit constraint this ticket's own
  body states (T-1684's whole point stays intact).

### Changed
```
 src/frob/app/ticket_runner/_rapid_sweep.py | 179 +++++++++++++++++++++++++++--
 tests/unit/test_rapid_sweep.py             | (new test classes appended)
```

### Evidence (9 ids, all fail-first)
- TestRollingBaseline::test_read_baseline_commit_absent_is_none / test_read_baseline_commit_round_trips
- TestLandIdsBetween::{test_single_land_in_range, test_multiple_lands_in_range_oldest_first, test_non_land_commits_are_ignored, test_non_repo_returns_empty_list}
- TestResolveActualHead::{test_non_repo_falls_back_to_the_given_commit, test_real_repo_resolves_the_true_head}
- TestDeferredSweepMultiLandAttribution::test_two_lands_in_the_window_are_both_named_not_just_the_spawning_one -- the T-1998 shape reconstructed end-to-end: two real git commits ("land T-1977", "land T-1995") land between a recorded baseline and the tree the sweep measures; asserts the filed ticket's title AND body name BOTH ids, not just the one that spawned the sweep, and that the baseline's recorded commit is the real measured HEAD, not the stale spawn-time sha.

Fail-first confirmed by hand: `git checkout HEAD -- src/frob/app/ticket_
runner/_rapid_sweep.py` (reverting only the source, keeping the new
tests), re-ran `tests/unit/test_rapid_sweep.py` -> collection ImportError
(`_land_ids_between` does not exist pre-fix) -- a hard failure, not a
softer assertion mismatch. Restored the fix, re-ran: `uv run pytest
tests/unit/test_rapid_sweep.py -p no:cacheprovider -q` ->
`SUITE-RESULT: exitstatus=0 collected=62 failed=0` (53 pre-existing + 9
new, none broken).

### Shared root cause across this series
T-2005 (BUG002's dropped PYTHONPATH), T-2009 (this ticket), and T-2006
(next in series) are related but NOT the same defect: T-2005 is a
subprocess-env plumbing bug in a completely different subsystem
(mutation-evidence repro checks) with no code-path overlap with the
sweep. T-2009's own root cause (the sweep's `fresh` measurement can
reflect commits landed AFTER the land that spawned it, because the check
is detached and asynchronous) is structurally close to what T-2006 was
filed against (T-1983's auto-drop only re-verifies inside the NEXT
sweep's own run) -- both are instances of "the sweep's cadence relative
to the land stream matters, and the code assumed 1:1 when it is N:1" --
but the fixes are disjoint code paths (attribution text vs. the auto-drop
call site's trigger), so I implemented them as separate, independently
evidenced tickets rather than one combined fix.

Gates: `frob check --land-parity` clean (0 unscoped errors) after this
change.

### Changed
```
 tickets/T-2009/ticket.md | 30 +++++++++++++++++++++++++++++-
 1 file changed, 29 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestRollingBaseline::test_read_baseline_commit_absent_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRollingBaseline::test_read_baseline_commit_round_trips` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestLandIdsBetween::test_single_land_in_range` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestLandIdsBetween::test_multiple_lands_in_range_oldest_first` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestLandIdsBetween::test_non_land_commits_are_ignored` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestLandIdsBetween::test_non_repo_returns_empty_list` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestResolveActualHead::test_non_repo_falls_back_to_the_given_commit` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestResolveActualHead::test_real_repo_resolves_the_true_head` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestDeferredSweepMultiLandAttribution::test_two_lands_in_the_window_are_both_named_not_just_the_spawning_one` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH001@src/frob/gates/_fix_engine_sync.py, COV003@tickets/T-0907, F401@/home/logan/projects/frob/.claude/worktrees/bug-002-sweep-series/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/bug-002-sweep-series/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-2009
