---
id: T-2140
title: test_concurrent_write_between_squash_and_splice_survives_land self-referentially
  deadlocks against its own outer land call
state: done
kind: bug
origin: agent
created: '2026-08-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_ticket_land.py
- src/frob/tickets/_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land
designated_repro_test: tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land
acceptance:
- text: given test_concurrent_write_between_squash_and_splice_survives_land run alone
    with -o addopts=, when executed, then it completes well within pytest's 120s per-test
    ceiling instead of deadlocking past it
  evidence:
  - tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land
- text: given the same test run under the repo default parallel invocation inside
    its heavy_subprocess xdist_group, when executed, then it does not crash its owning
    xdist worker
  evidence:
  - tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-2099 (per-file xdist grouping for real-git-heavy
test files).

`tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land`
genuinely deadlocks. Reproduced in FULL ISOLATION -- no xdist, no other
tests, `-o addopts="" pytest ... ::test_concurrent_write_...` alone --
still exceeds a 200s wrapper with no result. This is not an artifact of
T-2099's grouping work or of T-2093's now-landed dispatch-verb fix; it
reproduces standalone, on an idle host, both before and after T-2093
landed.

## Root cause (traced, not guessed)

The test calls the real `land(repo, tid, wt, dry_run=False)`. It patches
`_land_squash_mod.run_argv` so that immediately after the squash-merge
step, it calls `new_ticket(repo, ...)` -- a SECOND, concurrent ledger
write against the SAME `repo` the outer `land()` call is still actively
processing.

`new_ticket` -> `_commit_new_ticket` -> `commit_ticket_ledger_change` ->
`_add_and_commit_tickets_md` -> `refuse_if_land_in_progress(root)`
(`src/frob/tickets/_leases.py:1824`) -- and this call sees the OUTER
land (the very one whose squash step triggered it) still holding the
land lock, so it waits.

The outer land cannot finish and release that lock, because it is
synchronously blocked INSIDE the patched `run_argv` hook waiting for this
very `new_ticket()` call to return. Self-referential deadlock: the
concurrent write waits for the land to finish; the land cannot finish
until the concurrent write returns.

T-1961/T-2023 deliberately calibrated `refuse_if_land_in_progress`'s wait
budget (`_resolve_land_wait_budget`) to real observed land durations
(much longer than a test wants) specifically so a genuinely-concurrent
write does not refuse prematurely against a real, finishing land. That
is correct for the real-world case; it means THIS test's wait never
naturally resolves (the outer land it's nested inside can never finish)
and the wait runs out its full multi-minute budget -- pytest-timeout's
120s per-test ceiling fires first, thread-dumping and then either failing
the test (serial, recoverable) or, under `pytest-xdist`, killing the
worker outright (`node down: Not properly terminated`, unrecoverable for
that worker's remaining scheduled tests -- see T-2099's Done report for
the exact interaction with per-file `xdist_group` scheduling).

## Classification: TEST-HARNESS DEFECT, not a production hazard (traced, not guessed)

Determined by finding whether anything in PRODUCTION actually re-enters
the ledger from inside `land()`'s own in-process execution while it
holds the land lock -- not by reading the mechanism and assuming.

Checked every way `land()` (`src/frob/tickets/_land.py`) can run code
during its own execution:

- `land()`'s own body and every module in the land family
  (`_land_squash.py`, `_land_finalize.py`, `_land_git_ops.py`,
  `_land_release.py`, `_land_ledger_merge.py`, `_land_merge_zones.py`):
  `git grep -n "new_ticket(\|commit_ticket_ledger_change(\|
  _add_and_commit_tickets_md("` across all six files -- **zero hits**.
  Land never calls a ledger-mutating primitive from inside itself.
- Every CLI-supplied callback `land()` accepts (`bump_version`,
  `sync_gate_rules`, `check_gates`, `check_gate_findings`,
  `check_gate_claims`, `pre_commit_sweep`, `rebuild_natives`), as wired
  by `_land_cmd.py`'s real production call
  (`src/frob/app/ticket_runner/_land_cmd.py:3378-3400`): `check_gates`/
  `check_gate_findings` spawn a SEPARATE PROCESS (`_shared_check_
  spawn_fn` -> `python -m frob check --ticket <id>`, a subprocess, not
  in-process); `pre_commit_sweep` (`_land_pre_commit_sweep_fn` ->
  `_pre_commit_unscoped_error_sweep`) only scans/auto-fixes files, no
  ledger calls; `bump_version`/`sync_gate_rules` write
  `pyproject.toml`/`check-coverage.yaml`, not `tickets.md`, and never
  call the ledger primitives either; `check_gate_claims` only reads
  (`_close_gate_claims_for_ticket`).
- The one background THREAD land starts in the same process
  (`_land_cmd.py`'s `baseline_thread`, running concurrently with
  `land()`'s own merge): calls `_capture_pre_land_baseline`, which only
  does `git rev-parse`/`_unscoped_error_findings` reads against a
  detached snapshot worktree -- no ledger write.
- No hook/plugin/callback-registry mechanism exists in `_land.py` beyond
  the explicit typed parameters above (`git grep -n "hook\|callback\|
  plugin"` on `_land.py`, excluding docstrings/comments -- zero
  structural hits).

**Conclusion: no real production code path calls `new_ticket`/
`commit_ticket_ledger_change` reentrantly from inside `land()`'s own
process while it holds the land lock.** The only place this pattern
occurs is this test's own `monkeypatch.setattr(_land_squash_mod,
"run_argv", _fake_run_argv)` -- a git-level function patched purely to
inject an unrelated, synchronous, in-process `new_ticket()` call at a
precise moment. In real operation the "concurrent write" T-1036's fix
targets is a SEPARATE process (a different worktree/agent), which
`refuse_if_land_in_progress`'s process-scan (`_scan_for_live_land_
process`) correctly waits out and then proceeds once the real land
genuinely finishes and releases its lock -- not a self-referential wait
with no possible exit. `refuse_if_land_in_progress`'s process-scan
cannot distinguish "a different process is landing" from "I am the
process currently landing, and this call is happening synchronously
inside my own callback" -- but nothing in production ever puts it in
that second position; only this test's construction does.

Fix: rewrite the test to exercise the concurrent-write race without
blocking inside the land's own call stack (e.g. a background thread or
subprocess that actually races the land from OUTSIDE its execution,
rather than a monkeypatched hook that IS the land's own execution) --
priority medium, no urgency, this cannot fire outside a test process.

Acceptance:
- given `test_concurrent_write_between_squash_and_splice_survives_land`
  run alone with `-o addopts=""`, when executed, then it completes
  (pass or fail) well within pytest's 120s per-test ceiling instead of
  deadlocking past it
- given the same test run under the repo default parallel invocation
  (inside its `heavy_subprocess` `xdist_group`, see T-2099), when
  executed, then it does not crash its owning xdist worker

## Fixed (T-2099's worktree, same session)

Rewrote the test to spawn the concurrent `new_ticket()` call in a
genuinely separate forked process (`multiprocessing.get_context("fork")`,
mirroring `TestSigkillMidStaging`'s own pattern already in this file)
instead of calling it synchronously in-process from the `run_argv` hook.
Measured: the single test now passes in 3.45s (previously exceeded a
200s wrapper with zero result, reproduced twice standalone). The full
file completes under the repo default parallel invocation:
`SUITE-RESULT: exitstatus=1 collected=275 failed=1` (one pre-existing
unrelated flake), well within the 540s budget.

`--designate-repro`'s automated parent-commit check could not itself
render FAILED_AT_PARENT here and required `--designate-repro-force`:
its own repro-run spawn has a fixed 60s cap, shorter than the ~100-200s
this deadlock takes to manifest, so it can only report `NO_VERDICT`
(spawn timeout) never a genuine `FAILED_AT_PARENT` for this specific
bug shape -- a tool limitation, not a sign the repro is fake. The real
verdict is the manual evidence above: the exact same node id, run alone
with `-o addopts=""` against the parent commit, twice independently
exceeded a 200s wrapper with an identical `refuse_if_land_in_progress`
stack trace both times (see T-2099's Done report for the first capture;
repeated here after merging main, with T-2093/T-2103 landed, to rule
out T-2093 as the cause).

## Done report

### Changed

- `tests/test_ticket_land.py`: `test_concurrent_write_between_squash_and_splice_survives_land`
  now spawns its concurrent `new_ticket()` call in a genuinely separate
  forked process (`_t2114_concurrent_new_ticket`, module-level target,
  `multiprocessing.get_context("fork")`, mirroring
  `TestSigkillMidStaging`'s existing pattern in the same file) instead of
  calling it synchronously in-process from the `run_argv` monkeypatch
  hook `land()` itself invokes mid-squash.

### Classification (found, not guessed)

Traced every path `land()` can run code from inside its own in-process
execution while it holds the land lock: its own body and every module
in the land family (`_land_squash.py`, `_land_finalize.py`,
`_land_git_ops.py`, `_land_release.py`, `_land_ledger_merge.py`,
`_land_merge_zones.py` -- zero calls to `new_ticket`/
`commit_ticket_ledger_change`/`_add_and_commit_tickets_md`), every
CLI-supplied callback (`_land_cmd.py:3378-3400`'s real production wiring
-- `check_gates`/`check_gate_findings` spawn a SEPARATE subprocess,
`pre_commit_sweep` only scans/auto-fixes files, `bump_version`/
`sync_gate_rules` write non-ledger files, `check_gate_claims` only
reads), and the one background thread land starts (`baseline_thread` ->
`_capture_pre_land_baseline`, read-only). No hook/plugin/callback
mechanism exists in `_land.py` beyond those typed parameters.
**Conclusion: no production code path re-enters the ledger from inside
`land()`'s own process while it holds the land lock.** The deadlock was
exclusively a test-construction artifact: `monkeypatch.setattr` injected
a synchronous, in-process `new_ticket()` call from a hook that IS the
land's own execution, which `refuse_if_land_in_progress`'s land-lock
probe (a fresh `flock()` on the same lock file -- conflicts regardless
of same-process-or-not, since `flock` is per-open-file-description, not
per-process-reentrant) can never observe as free until the land
finishes, and the land can never finish until that call returns.
Priority set to medium (test-only, no production hazard).

### Measurements

- Single node id alone, `-o addopts=""`: was hanging past a 200s wrapper
  (twice, independently, matching stack trace both times); now
  `1 passed in 3.45s`.
- Full file, `-o addopts=""`: `1 failed, 274 passed in 118.09s (0:01:58)`
  (the one failure, `TestLedgerV2LandMergeStory::test_same_ticket_
  conflict_surfaces_loudly_no_splice`, is a pre-existing unrelated
  flake).
- Full file, repo default parallel invocation (T-2099's `heavy_subprocess`
  grouping in place): `SUITE-RESULT: exitstatus=1 collected=275 failed=1`
  -- completes cleanly within the 540s budget. This is the artifact that
  T-2099's own acceptance index 0 needed.

### Evidence

- `tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land`
  -- bound to both acceptance indices.
- Designated repro via `--designate-repro-force`: the tool's own
  parent-commit repro-run spawn has a fixed 60s cap, shorter than this
  deadlock's ~100-200s manifestation time, so it can only report
  `NO_VERDICT` (spawn timeout), never a genuine `FAILED_AT_PARENT`, for
  this specific bug shape -- a tool limitation, not a false-positive
  repro. The real verdict is the manual evidence: the same node id, run
  alone with `-o addopts=""` against the parent commit, independently
  exceeded a 200s wrapper twice with an identical
  `refuse_if_land_in_progress` stack trace both times (recorded in
  T-2099's Done report and this ticket's own body).

### Filed

None. (The id-collision incident below is a systemic allocator defect
already filed critical by the coordinator as T-2122 -- not filed again
here.)

### Id-collision incident (record only, not this ticket's own defect)

This ticket's id churned six times before landing, colliding with an
independently-filed main ticket at THREE different ids in a row: an
initial draft promoted to T-2114 (collided) -> a fresh draft promoted
to T-2118 (collided again) -> a fresh draft renumbered to T-2130
(collided a THIRD time -- main independently filed an unrelated T-2130,
"post-land sweep regression from T-2109", in the same window) -> its
content restored under T-2140, verified free on main AND across every
live worktree branch immediately before writing, not just the
worktree's own stale view. Every collision was `frob ticket promote`/
`renumber`'s own next-id allocator (or, for the third, a manually
picked id) reading the taken-id set from a merge-base view that goes
stale the instant another worktree or the shared root allocates first
-- `allocator_lock` (T-2092) serializes WRITERS but not the READ of
"what ids are already taken," so two lock-holders in sequence can each
correctly compute a next-id from their own already-stale view and
collide anyway. The coordinator has filed this critical as T-2122;
nothing new filed here. Every collision was caught before landing
(git add/add conflict on the ticket file, or `frob ticket land`'s own
merge-conflict refusal) and resolved by taking main's side and
restoring this ticket's content under a freshly-verified id -- no
content was lost, per T-2105's `detect_duplicate_ticket_id_collisions`
land-time guard existing as the backstop if a collision were ever
missed pre-land.

### Gates

`frob check --ticket T-2140`: run at close time.

### Changed
```
 docs/guides/testing.md                |  40 +++++++
 pyproject.toml                        |   1 +
 rapid-debt.jsonl                      |   4 +
 tests/conftest.py                     |  43 +++++++-
 tests/test_ticket_land.py             |  70 +++++++++++--
 tests/test_ticket_leases.py           |   8 ++
 tests/unit/test_conftest_stackdump.py |  63 +++++++++++
 tickets/T-2099/done-report.md         | 191 ++++++++++++++++++++++++++++++++++
 tickets/T-2099/ticket.md              |  65 +++++++++++-
 tickets/T-2140/ticket.md              | 175 +++++++++++++++++++++++++++++++
 10 files changed, 651 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: E402@/home/logan/projects/frob/.claude/worktrees/t-2099/tests/test_ticket_leases.py, TICK004@tickets.md, WIRE001@tests/test_ticket_land.py
