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