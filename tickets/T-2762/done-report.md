## Done report

Changed:
- tests/conftest.py::_SELF_SCAN_HEAVY_NAME_SUBSTRINGS (added 4 names)

Approach: T-1654's audit had already narrowed the candidate set to exactly
4 real-repo-root build_graph/_load_inputs tests (the other 2 of the 6
originally-flagged files were confirmed tmp_path-isolated and clear), but
declined to add them speculatively because a scoped 4-test/2-worker run did
not meet T-1635's own evidentiary bar (a real pytest -n auto run tripping
the timeout with a faulthandler trace showing derived_state_lock
contention).

I reproduced that bar directly rather than adding the names speculatively:
running all NINE real-repo-root self-scans together (the five already in
_SELF_SCAN_HEAVY_NAME_SUBSTRINGS plus these four candidates), ungrouped, at
-n 9 --dist loadgroup crashed 3 xdist workers with "node down: Not properly
terminated" (gw8/gw2/gw4), and a PYTHONFAULTHANDLER=1 thread dump caught
tests/test_waive_gate.py::TestWaive006RealRepo::test_zero_errors_on_real_repo
blocked inside derived_state_lock/derived_state_write_lock
(src/frob/process/_lock.py) via build_graph <- _load_inputs -- the identical
call chain the other five already-grouped tests block on per T-1635's own
comment. This is the same contention shape, reproduced with the same tool
(PYTHONFAULTHANDLER + timeout -s ABRT) previously used to find a hotspot in
this repo in ~180s.

Fix: added the four test names' distinguishing substrings
("test_zero_errors_on_real_repo", "test_zero_findings_on_real_repo",
"test_real_repo_scan_runs_end_to_end_without_crashing",
"test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses") to
_SELF_SCAN_HEAVY_NAME_SUBSTRINGS, following the T-1635 precedent exactly --
no other code change, matching the ticket's own "the mechanism is a
straightforward substring append" prediction.

Verified the fix: re-ran the SAME nine tests together at -n 2 (mirroring
T-1654's own sanctioned methodology) -- all nine ran to completion with no
worker crashes and no scheduler timeout (previously-passing pytest exit,
just 4 pre-existing unrelated assertion failures about live repo state --
SYS107/SELFAUDIT001/REG008 findings on this worktree's own current tree,
confirmed to fail identically when run standalone/serially, i.e. unrelated
to xdist scheduling and outside this ticket's scope). Also confirmed
tests/unit/test_conftest_stackdump.py (8 tests, including the grouping
mechanism's own regression test) and tests/unit/test_conftest_parse_reset.py
(3 tests) still pass after the edit.

One incidental, unrelated observation not part of this ticket's fix: at
-n 9 with only these 9 items collected (no other test items for idle
workers to pick up), pytest-xdist's own loadscope scheduler hit an
INTERNALERROR (KeyError in _assign_work_unit, xdist/scheduler/loadscope.py)
when idle workers had zero collected items left after the sole heavy group
was assigned -- a scheduler artifact of an artificially tiny corpus (a real
full-suite run always has other work for idle workers), not a contention
finding and not something this ticket's scope (tests/conftest.py only)
covers a fix for.

Evidence: tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_self_scan_heavy_tests_share_one_xdist_group

Filed: none (the xdist scheduler INTERNALERROR above is a pre-existing
pytest-xdist behavior triggered only by an artificially small item set,
not a real full-suite reachable defect -- not filing speculative noise per
this ticket's own "no ticket needed" standard).

Gates: frob check --ticket T-2762 --only gates-fast: gate:SCOPE 0 errors
(clean), gate:AFFECT clean (no affects()-closure edges touched by this
symbol). Remaining gate-summary failures (gate:COV/DOC/DRIFT/TEST/TICK) are
repo-wide, pre-existing, and touch files this ticket's diff never modified
(verified via git diff --stat) -- per the tool's own gate:scope-note, those
families are not filtered to this ticket's scope.

### Changed
```
 tests/conftest.py        | 27 +++++++++++++++++++++++++++
 tickets/T-2762/ticket.md |  4 ++++
 2 files changed, 31 insertions(+)
```

### Evidence
- `tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_self_scan_heavy_tests_share_one_xdist_group` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 17 error(s), 819 warning(s), 708 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, E501@/home/logan/projects/frob/.claude/worktrees/t2760-t2762/src/frob/tickets/_new_renumber.py, PERF004@src/frob/tickets/_evidence.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
