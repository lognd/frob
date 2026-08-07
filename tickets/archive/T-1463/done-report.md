## Done report

`frob ticket land` ran two sequential unscoped, budget-bounded `frob check`
spawns (`_capture_pre_land_baseline` before `land()`, `_post_land_
unscoped_error_sweep`'s fresh scan after) plus a potential third
(`reverify`, only on the new-findings branch) -- easily exceeding the
playbook's 540s foreground budget on their own, independent of
`land()`'s own worktree-scoped checks. Neither of the two mandatory scans
can share T-1346's digest-keyed gate cache with each other: they run
against genuinely different tree states by design (before vs. after
`land()`'s merge), so cache reuse across them was never actually
available -- the redundancy was in HOW MANY scans ran, not a cache miss
bug.

Two fixes, both in `src/frob/app/ticket_runner/_land_cmd.py`:

1. `_capture_pre_land_baseline` now scans an isolated, detached `git
   worktree` snapshot at the pre-land HEAD sha
   (`_spawn_baseline_snapshot_worktree`/`_remove_baseline_snapshot_
   worktree`) instead of `root` directly. This is what makes it SAFE to
   run the whole baseline capture in a background thread, started in
   `_land` before `land(...)` is called and joined only once its result
   is actually needed (right before `_run_post_land_sweep_or_exit`): a
   background scan reading `root`'s live tree directly would race
   `land()`'s own merge writing to those same files mid-scan, producing a
   baseline that is neither the true pre-land nor post-merge state.
   Scanning an immutable snapshot instead removes that race entirely, so
   the baseline scan's wall time now overlaps with whatever `land()`
   spends on its own worktree-scoped checks instead of adding on top of
   it sequentially.
2. `_post_land_unscoped_error_sweep`'s Tier-A reverify spawn (previously
   unconditional whenever any new finding existed) is now skipped when
   `_sweep_apply_tier_a_and_commit` applied 0 fixes -- `root`'s tree is
   provably unchanged since the `fresh` scan a few lines above, so a
   second full scan is guaranteed to reproduce the identical result.
   `fresh` is reused directly as `reverify` in that case.

Verified directly (isolated smoke test, not the full `land()` path, since
exercising a real `frob ticket land` end to end from inside this session
would land my own in-progress work): built a throwaway git repo, called
`_spawn_baseline_snapshot_worktree`/`_remove_baseline_snapshot_worktree`
directly -- confirmed the detached worktree is created at the given sha,
contains the expected tracked file, and is cleanly removed afterward with
no leaked registration (`git worktree list` clean).

Existing test suite (`tests/test_ticket_work_and_land_finish.py`, all 12
tests, `TestPostLandUnscopedSweep`'s 4 tests included) passes unchanged --
these monkeypatch `_unscoped_error_findings` directly, so the reverify-skip
optimization and the snapshot-based baseline capture are exercised through
the same seams these tests already cover; none needed changes since the
externally observable contract (same findings, same refuse/no-op/auto-fix
decisions) is unchanged.

Cut, disclosed rather than silently dropped: the ticket's acceptance also
names updating "the foreground-budget hook and playbook section 3b
guidance ... to whatever the fixed land's real worst case is" -- that is a
`.claude/settings.json`/`docs/guides/agent-playbook.md` change, outside
this ticket's declared scope (`src/frob/app/ticket_runner/_land_cmd.py`,
`src/frob/tickets/_land_finalize.py`). A coordinator should measure a real
land's new worst-case wall time post-fix and file that as its own
follow-up, or extend a future ticket's scope to cover it -- not something I
should silently fold in here or expand scope for myself.

Known, expected multi-ticket-worktree artifact (not a T-1463 regression):
`frob check --ticket T-1463` reports 2 `gate:SCOPE` SCOPE001 errors, on
`src/frob/gates/_secrets.py` and `src/frob/graph/cache.py` -- these are
T-1211's and T-1214's own changes, committed earlier in this same
worktree/branch but not yet landed to main, still showing in the
ticket-scoped diff against main. Will resolve once those land.

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py | 148 ++++++++++++++++++++++++++++++--
 src/frob/gates/_secrets.py              |  79 ++++++++++++++++-
 src/frob/graph/cache.py                 |  51 +++++++++--
 tickets.md                              | 137 +++++++++++++++++++++++++++--
 4 files changed, 391 insertions(+), 24 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 273 warning(s), 743 waived
- error-findings: none (measured, zero errors)
