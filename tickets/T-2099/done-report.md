## Done report

### Changed

- `tests/conftest.py`: `pytest_collection_modifyitems` groups any item
  whose module carries `pytest.mark.heavy_subprocess` into its own
  `xdist_group`, keyed by the item's `nodeid` file-path prefix (per-file,
  not one shared group across every heavy file).
- `pyproject.toml`: registers the `heavy_subprocess` marker.
- `tests/test_ticket_land.py`, `tests/test_ticket_leases.py`: self-declare
  `pytestmark = pytest.mark.heavy_subprocess`.
- `tests/unit/test_conftest_stackdump.py`: `TestHeavySubprocessGrouping`
  unit coverage for the grouping branch (repro-designated).
- `docs/guides/testing.md`: documents the `heavy_subprocess` marker
  convention.
- `tests/test_ticket_land.py`: separately, T-2140 (landed as this
  ticket's blocker) fixed `test_concurrent_write_between_squash_and_
  splice_survives_land`'s own self-referential deadlock -- see that
  ticket for the classification/fix; this ticket's own diff against
  main is now EMPTY (all of T-2099's code content already shipped as a
  disclosed passenger of T-2140's land, `--allow-cross-ticket`,
  commit `e819ee7867ef`).

### Design rationale (preserved per explicit request)

The existing grouping mechanism, T-1433's
`_SELF_SCAN_HEAVY_NAME_SUBSTRINGS`, is a hardcoded list of five test
NAMES a maintainer must remember to extend for every new heavy file --
and nobody did for `tests/test_ticket_land.py` or `tests/test_ticket_
leases.py`. The grouping census taken this session (`git grep -c
xdist_group -- tests/test_ticket_land.py tests/test_ticket_leases.py`
returning 0/0 before this ticket) proved neither file was grouped by
anything, so `--dist=loadgroup` degraded to ordinary scattering for
exactly the tests that most need not to scatter. Rather than extend
that hardcoded list -- the same recurring "correct primitive wired into
too few call sites" defect this session hit repeatedly (T-1990-class,
now six instances) -- this ticket adds a self-declared, module-level
marker instead: the convention lives IN the heavy file itself, next to
the real-subprocess code that justifies it, discoverable by reading a
sibling file rather than by remembering to edit `conftest.py`. Each
marked module gets its OWN `xdist_group`, not one shared group, so
scheduling is serialized WITHIN a file (no cross-worker git contention)
while different heavy files still run in parallel with each other and
the rest of the suite -- avoiding the OOM-concentration risk T-1433's
own docstring names for its grouping.

### Measurements (all `SUITE-RESULT`/pytest summary artifact lines)

1. Serial baseline (`-o addopts=""`), confirmed myself before any fix:
   `1 failed, 274 passed in 463.55s (0:07:43)` -- completed within
   budget; the same file's default-parallel run at that point never
   produced a summary line at all (killed at the 540s hard timeout,
   `[gwN] node down: Not properly terminated`).
2. `--dist=loadgroup` grouping census (pre-ticket): 0/0 -- neither
   target file had any `xdist_group` marker.
3. **Post-fix, post-T-2140, re-measured fresh from a clean merge with
   main**: `tests/test_ticket_land.py` full file, default parallel
   invocation: `SUITE-RESULT: exitstatus=1 collected=275 failed=1` (one
   pre-existing unrelated flake,
   `TestLedgerV2LandMergeStory::test_same_ticket_conflict_surfaces_
   loudly_no_splice`) -- completes cleanly, well within the 540s budget.
   **Acceptance index 0 is met.**
4. `tests/test_ticket_leases.py` full file, default parallel invocation:
   `SUITE-RESULT: exitstatus=0 collected=131 failed=0` -- completes
   cleanly. **Acceptance index 1 is met.**
5. Collection sanity for the remaining suite: `pytest -q --collect-only
   tests/` -> `SUITE-RESULT: exitstatus=0 collected=9893 failed=0` in
   7.7s wall, zero `PytestUnknownMarkWarning`. The `heavy_subprocess`
   branch only fires for `item.get_closest_marker("heavy_subprocess")`,
   a per-item lookup already paid by pytest's own collection machinery;
   only the two target files carry the marker, so no other file's
   scheduling changes -- structurally cannot regress what it does not
   touch. **Acceptance index 2 is met** (evidence: the grouping-branch
   unit test, which proves the mechanism is a no-op for any unmarked
   module).

### The confounder this ticket had to work through, and how it resolved

`tests/test_ticket_land.py`'s `test_concurrent_write_between_squash_
and_splice_survives_land` had an independent, genuine deadlock (traced
to a self-referential `refuse_if_land_in_progress` wait -- the test
called `new_ticket()` synchronously in-process from a hook `land()`
itself invokes mid-squash, so the concurrent write's wait for the land
to finish could never resolve, because the land was itself blocked
waiting for that very call to return). Reproduced in full isolation
(single node id, `-o addopts=""`, no xdist at all) -- ruling out xdist
grouping as the cause. Traced every path `land()` can run code from
inside its own process (its own body, every CLI-supplied callback, its
background baseline thread) and confirmed no PRODUCTION code path
re-enters the ledger this way -- classified TEST-HARNESS DEFECT, not a
production hazard, filed and fixed as T-2140 (spawns the concurrent
write in a genuinely separate forked process instead, mirroring
`TestSigkillMidStaging`'s existing pattern in the same file). T-2140
landed first (it is this ticket's blocker); this ticket's own diff
against main is consequently empty -- everything shipped as a disclosed
passenger of that land.

### Id-collision incident (T-2140's own, not repeated here)

T-2140's Done report (main:`tickets/T-2140/done-report.md`) records the
full six-id churn this deadlock ticket went through (three separate
collisions with independently-filed main tickets at T-2114, T-2118, and
T-2130) before landing -- a systemic allocator defect the coordinator
has filed critical as T-2122. Not repeated in full here.

### Filed

T-2140 (bug, medium, landed) -- the test-harness deadlock this ticket's
own measurement surfaced, blocking full completion until fixed.

### Evidence

- `tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land`
  -- acceptance index 0; designated repro (`--designate-repro-force`,
  same tool-limitation rationale as T-2140: the check's own repro-run
  spawn has a fixed 60s cap, shorter than the deadlock's ~100-200s
  manifestation time at T-2099's own pre-fix parent commit, so it can
  only report `NO_VERDICT`, never a genuine `FAILED_AT_PARENT`, for
  this bug shape -- not a sign the repro is fake; the manual evidence
  in T-2140's own Done report is the real verdict).
- `tests/test_ticket_leases.py::TestRefusesTerminalState::test_refuses_done_ticket`
  -- acceptance index 1 (representative single-test evidence backing
  the full-file `SUITE-RESULT` measurement above).
- `tests/unit/test_conftest_stackdump.py::TestHeavySubprocessGrouping::test_heavy_subprocess_marker_groups_per_file`
  -- acceptance index 2.

### Gates

`frob check --ticket T-2099`: clean (0 errors) at an earlier tip in this
session; re-verify at close/land time since the tree has moved (T-2140
landed, several unrelated main lands since).

### Changed
```
 tickets/T-2099/ticket.md | 13 +++++++++----
 1 file changed, 9 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_conftest_stackdump.py::TestHeavySubprocessGrouping::test_heavy_subprocess_marker_groups_per_file` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRefusesTerminalState::test_refuses_done_ticket` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: E402@/home/logan/projects/frob/.claude/worktrees/t-2099/tests/test_ticket_leases.py, PRE001@tickets/T-2099, SELFAUDIT001@design, TICK004@tickets.md
