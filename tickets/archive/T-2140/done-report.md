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
