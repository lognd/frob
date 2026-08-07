## Done report

Extracted the "doable/leases/scope-breadth" family named in T-1108's own
scope note out of tickets/__init__.py into a new src/frob/tickets/_doable.py
module, following T-1103's exact split pattern (private module re-exported
from __init__ via explicit imports, zero caller-visible behavior change).

Moved: _doable_candidates, _in_progress_leases, _cross_worktree_leases,
_all_leases, _is_excluded_breadth_path, _repo_files_git,
_repo_files_walk_fallback, _repo_files, scope_breadth_context,
_entry_to_glob, _over_broad_scope_entries, large_glob_warnings, leased_by,
display_state, has_live_lease, _DISPATCH_STALE_DEFAULT_HOURS,
_dispatch_stale_thresholds, dispatch_stale_hours, undispatched_stale,
doable, doable_blocked, _open_blockers.

tickets/__init__.py: 3489 -> 2918 lines (571 carved). Below the acceptance
criterion's <2000 target -- this is a PARTIAL land (T-1089 precedent):
one cohesive family this dispatch, remaining ~7 families (scope mutation,
field setters/sprint, evidence/transition, done-report/review/drop/attach)
plus the untouched _land.py (4762 lines) split are filed as residue
(T-1123, real id assigned at land-time renumber).

Hit two of T-1103's own flagged hazard classes directly:
1. `_doable_sort_key` (board_view's sort key too) and `_OPEN_STATES`
   (a module-wide constant) stay in __init__.py; the moved `doable`/
   `doable_blocked`/`_open_blockers` late-import both from the package at
   call time rather than binding them at module load, since __init__
   imports _doable.py before either name exists at __init__'s own module
   scope -- the exact load-order hazard T-1103's Done report named for
   `renumber_one`.
2. Monkeypatch indirection: `tests/test_tickets_lease.py::TestBreadthPerf`
   and `tests/test_tickets_dispatch_stale.py::TestHasLiveLease` /
   `tests/test_tickets_lease_overlay.py::TestDisplayState` monkeypatch
   `frob.tickets._repo_files` / `frob.tickets.read_all_leases` (the PACKAGE
   attribute) -- a plain module-top-level `import` binding in _doable.py
   would not see that patch. `scope_breadth_context` and `display_state`
   both late-import these from the package instead, same fix T-1103 applied
   for `renumber_one`/`finalize_draft`. Caught this by running the full
   affected test suite BEFORE committing, not by inspection alone -- 4
   tests failed on the first pass with exactly this symptom.

Also: re-ran `frob ack src/frob/tickets/__init__.py::_recover_missing_evidence_for_done`
-- moving ~570 lines out of the same file shifted this unrelated function's
digest, invalidating its pre-existing DRIFT001 ack (the same "reviewer
re-acks at land" pattern T-1103's Done report already named for this exact
symbol).

Confirmed via `git diff main -- <file>` that the two INV006 findings
(src/frob/gates/_todo_fmt.py, src/frob/gates/_waive_comments.py) and the
three TICK006 phantom-draft findings (T-1077/T-1084/T-1095's historical
Done reports) `frob check --ticket T-1108` still reports are unrelated,
pre-existing, and untouched by this diff.

One pre-existing, unrelated test failure noted for visibility, NOT part of
this ticket's scope (tests/test_tickets_review.py is untouched by this
diff, confirmed via `git diff main`): TestCloseStrictMode's 4 tests fail
because `frob ticket close`'s evidence re-validation spawns `uv run pytest
--collect-only` inside an isolated tmp_path fixture with no real project
layout, collecting 0 tests -- an environment/infra issue in the
evidence/close family, not the doable family this ticket touched.

### Changed
```
 docs/modules/tickets.md      |  14 +-
 frob.lock                    |   2 +-
 src/frob/tickets/__init__.py | 616 ++-------------------------------------
 src/frob/tickets/_doable.py  | 671 +++++++++++++++++++++++++++++++++++++++++++
 tests/test_tickets.py        |   2 +-
 tests/test_tickets_tiers.py  |   4 +-
 tickets.md                   |  39 ++-
 7 files changed, 738 insertions(+), 610 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestDoable::test_blocked_excluded` (pytest node id, verified passing when recorded)
- `tests/test_tickets_tiers.py::TestDoableLeafOnly::test_epic_and_story_never_surface` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestDoable::test_ignore_lease_returns_raw_list` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestShowBlocked::test_show_blocked_lists_reasons` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestLeasedBy::test_precise_in_progress_does_not_hide_disjoint` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestLeasedBy::test_real_source_scope_collision_is_hidden` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestLeasedBy::test_over_broad_lease_demotes_to_warn_only` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestLargeGlobWarnings::test_fires_on_broad_tests_glob` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestLargeGlobWarnings::test_silent_on_precise_test_file` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestBreadthPerf::test_computed_once_per_doable_call` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestBreadthPerf::test_doable_blocked_also_shares_one_breadth_walk` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestBreadthPerf::test_repo_files_git_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease_overlay.py::TestDisplayState::test_queued_with_live_lease_decorated` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease_overlay.py::TestDisplayState::test_queued_with_stale_lease_undecorated` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease_overlay.py::TestDisplayState::test_ledger_in_progress_undecorated` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease_overlay.py::TestDisplayState::test_no_root_never_decorates` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_queued_with_live_lease_is_in_flight` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_queued_with_no_lease_is_not_in_flight` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_no_root_never_in_flight` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestDispatchStaleHours::test_same_day_is_zero_hours` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestDispatchStaleHours::test_one_day_old_is_24_hours` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_critical_past_threshold_alarms` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_critical_under_threshold_no_alarm` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_medium_priority_never_alarms` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 24 passed (from 24 evidence id(s))
- gates: 8 error(s), 878 warning(s), 425 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/w17-tickets/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w17-tickets/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w17-tickets/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w17-tickets/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w17-tickets/src/frob/vet/_supplychain.py:295, INV006@src/frob/gates/_todo_fmt.py, INV006@src/frob/gates/_waive_comments.py, TICK006@tickets.md
