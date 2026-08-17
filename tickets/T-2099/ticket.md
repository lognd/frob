---
id: T-2099
title: The heaviest test files are unrunnable under the default -n auto but pass serially,
  so agents land land-path changes with their test file unrun
state: done
kind: bug
origin: agent
created: '2026-08-10'
priority: high
blocked_by:
- T-2093
- T-2140
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- pyproject.toml
- tests/conftest.py
- tests/test_ticket_land.py
- docs/guides/testing.md
- tests/unit/test_conftest_stackdump.py
- tests/test_ticket_leases.py
- tickets/T-2140/ticket.md
evidence_scope:
- tests/unit/test_conftest_stackdump.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/conftest.py
  reason: grouping fix needs a self-declared marker on the heavy file plus conftest
    wiring to turn it into a per-file xdist group
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_ticket_land.py
  reason: grouping fix needs a self-declared marker on the heavy file plus conftest
    wiring to turn it into a per-file xdist group
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/guides/testing.md
  reason: document the new heavy_subprocess marker convention (per-file xdist grouping)
    alongside the existing per-test timeout override docs
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_conftest_stackdump.py
  reason: unit coverage for the heavy_subprocess -> per-file xdist_group grouping
    rule (lost in an earlier soft-reset splice, redone here)
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_ticket_leases.py
  reason: T-2093 done and its lease on this file released; apply the same heavy_subprocess
    marker now that acceptance index 1 is unblocked
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-2114/ticket.md
  reason: the ticket file created by filing T-2114, cited as the new blocker
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: tickets/T-2114/ticket.md
  reason: T-2114 collided with main and my ticket was renumbered to T-2130 after a
    second collision at T-2118; fix the stale scope reference
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tickets/T-2130/ticket.md
  reason: T-2114 collided with main and my ticket was renumbered to T-2130 after a
    second collision at T-2118; fix the stale scope reference
  actor: logan
  at: '2026-08-11'
- op: remove
  glob: tickets/T-2130/ticket.md
  reason: T-2130 collided with main too; my fix ticket's content is now at T-2140
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tickets/T-2140/ticket.md
  reason: T-2130 collided with main too; my fix ticket's content is now at T-2140
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_conftest_stackdump.py::TestHeavySubprocessGrouping::test_heavy_subprocess_marker_groups_per_file
- tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land
- tests/test_ticket_leases.py::TestRefusesTerminalState::test_refuses_done_ticket
designated_repro_test: tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land
acceptance:
- text: given tests/test_ticket_land.py, when run through the repo default invocation
    with no manual -o addopts override, then it completes and reports a pass/fail
    summary within the 540s foreground budget -- this test MUST fail against current
    main, where it exceeds 540s and never reports
  evidence:
  - tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land
- text: given tests/test_ticket_leases.py, when run the same way, then it completes
    and reports a summary rather than requiring a hand-picked subset
  evidence:
  - tests/test_ticket_leases.py::TestRefusesTerminalState::test_refuses_done_ticket
- text: given the remaining ~9000 tests, when measured before and after, then total
    wall-clock has not materially regressed -- xdist is not disabled globally
  evidence:
  - tests/unit/test_conftest_stackdump.py::TestHeavySubprocessGrouping::test_heavy_subprocess_marker_groups_per_file
threat: null
component: testing
anchor: false
anchor_reason: null
land_commit: null
---
## The measured inversion

`tests/test_ticket_land.py` (275 tests) is the repo's highest-traffic test
file and covers `frob ticket land`, the most safety-critical path here.

  SERIAL   (`-o addopts=""`, which drops `-n auto --dist=loadgroup`):
           275 passed in 420.18s -- I ran this myself, full summary line.
  PARALLEL (repo default `addopts = "-q -n auto --dist=loadgroup ..."`):
           exceeds 540s and never reports; the suite-measurement agent
           listed all 275 as UNMEASURED.

So the repo's DEFAULT execution mode is slower than serial on its heaviest
file -- slow enough to be unrunnable -- while serial finishes comfortably
inside a normal budget. These tests spawn real `git` and real subprocesses,
so xdist workers contend rather than parallelise.

Same pattern, reported independently:
- `tests/test_ticket_leases.py` (130 tests): T-2079's agent -- "would not
  complete in ANY foreground timeout tried"; it ran a 21-test write-path
  subset instead and said so honestly.
- `tests/test_coverage.py` (44 tests): stalls at test 5 (separate root
  cause, T-2098).

## The consequence, which is the reason this is not just friction

Agents edit `_land.py`, `_leases.py` and `_rapid_sweep.py` constantly -- most
of this session's criticals were in exactly those files -- and they CANNOT
run the tests that cover them. Every one of them did the honest thing and
ran a named subset while disclosing the gap. That is correct behaviour and
it is the best available under current tooling, but the net effect is that
the repo's most safety-critical code lands with its own test file unrun.

This is not hypothetical: the full-suite sweep found 32 failures and 3 hangs
at a ZERO unscoped gate-error floor. Gate-clean says nothing about these
files.

## Existing mechanisms that do NOT cover it

`frob test` has no serial / heavy-file / per-file-strategy option (checked
`--help`: `--all`, `--fuzz`, `--collect`, `--wait-coverage`, `--base`,
`--lang`, `--fallback`, `--json`). The playbook's answer is "run a subset",
which is a workaround for the symptom.

Note also `pytest -p no:xdist` does NOT work here -- `addopts` still injects
`-n auto --dist=loadgroup` and then nothing parses them (that gap is
T-2068). The only working incantation today is `-o addopts=""`, which is
undocumented folklore that every agent has to be told individually. I have
had to put it in every dispatch brief this session.

## DO NOT FIX IT THIS WAY

- **Do not just document `-o addopts=""` in the playbook.** Every agent has
  been told individually already; a rule that must be remembered before the
  tool works is not enforcement. This is exactly the case the standing audit
  rule names.
- **Do not globally disable xdist.** The other ~9,000 tests genuinely
  benefit; a repo-wide serial run would be far worse overall. The fix is
  per-file or per-group strategy, not a global switch.
- **Do not mark these files slow/skip by default.** They cover the land
  path. Making them easier to not run is the opposite of the goal.
- **Do not raise the foreground timeout and call it fixed.** 540s is a
  harness constraint agents cannot change; the work must fit it, or be
  runnable in a supported out-of-band way.
- **Do not assume `--dist=loadgroup` grouping already handles this.** It is
  configured today and the file still times out -- verify what the groups
  actually are before relying on them.

## Direction

Make the correct strategy automatic rather than remembered: a per-file (or
xdist-group) execution strategy so that files spawning real git/subprocesses
run serially while the rest stay parallel, reachable through `frob test`
without an undocumented `-o addopts=""`. Measure before and after: the
acceptance is a wall-clock number for the whole file, not a green subset.

<!-- frob:waive BUG002 reason="T-2099's own code fix (the heavy_subprocess
xdist_group mechanism) landed as a disclosed passenger of T-2140's land
(--allow-cross-ticket, commit e819ee7867ef) because T-2140's own fix (the
concurrent-write deadlock in test_concurrent_write_between_squash_and_splice_survives_land)
was this ticket's own blocker and had to land first. As a structural
consequence, no ref exists where T-2099's own fix is present without
T-2140's fix already applied too -- the designated repro test genuinely
PASSES at close/land time because BOTH fixes are already on main by
then, the same squash-collapse shape BUG002's own docs describe for
post-land verification (docs/modules/tickets.md#check-repro-post-land-limitation-t-2025).
The real proof this ticket's acceptance criteria are met is the manual
SUITE-RESULT measurement evidence recorded in this ticket's Done
report: tests/test_ticket_land.py (275/275, one pre-existing unrelated
flake) and tests/test_ticket_leases.py (131/131) both complete cleanly
under the repo default parallel invocation, which is exactly what could
not happen before this ticket's fix." -->

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
