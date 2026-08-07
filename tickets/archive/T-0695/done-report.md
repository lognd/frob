## Done report

Added `frob.arch._concurrency` (T-0695): four structural fork/pool hazard
checks -- `pool-inside-pool`, `fork-after-threads`, `pipe-wait-deadlock`,
`self-join-deadlock` -- each a fail-closed, syntactic co-occurrence
heuristic over one parsed python file's function bodies, on the same
unwaivable advisory channel every other `frob.arch` category is on
(`frob.gates._unwaivable_channel_rules` auto-adopts any new `ArchCategory`
value, so no gates-module change was needed).

Verified the acceptance criterion directly: `analyze_project` run against
`src/frob/gates` fires `pool-inside-pool` on
`src/frob/gates/__init__.py::_run_combined_jobs` as it exists today (its
`ProcessPoolExecutor` construction sits in the same function as the
`ThreadPoolExecutor` `with` block, the exact T-0265 shape) -- pinned as
`TestForkPoolHazards.test_pool_inside_pool_discharges_on_real_repo_run_combined_jobs`.
`_run_combined_jobs` cannot be waived (T-0101's unwaivable channel covers
every `frob.arch` category including the four new ones), so the finding
stays permanently visible in `frob check`'s frob-arch summary by design --
this is the correct terminal state per the ticket's "fail-closed advisory
on opaque dispatch" framing, not something to work around.

Severity note: `ArchSeverity` has no literal `"error"` tier (only
`warning`/`suggestion`/`info`); every finding uses `severity="warning"`,
the highest tier the type allows and the same tier the sibling ARCH1xx
families (T-0616/T-0617) use for their advisory-channel findings. I read
the acceptance's "error-tier finding" as this top tier, not a literal
gate-blocking `Violation` -- changing that categorization would mean
touching `frob.gates`/`frob.check` (both out of this ticket's scope) and
would be a bigger, separate design change (wiring a real gate rule the
way ARCH001 exists for long-function) that the ticket did not ask for.
Flagging this interpretation explicitly rather than silently assuming it.

Scope: added `docs/modules/arch.md` to the ticket's scope (reason
recorded in the ticket's `scope_changes`) since every existing
`frob.arch` check category carries a `frob:doc` anchor into this file and
DOCUMENT AS YOU GO requires the new checks follow the same pattern.

### Changed
```
 docs/modules/arch.md          |  50 ++++++
 src/frob/arch/__init__.py     |   3 +-
 src/frob/arch/_concurrency.py | 350 ++++++++++++++++++++++++++++++++++++++++++
 src/frob/arch/_models.py      |  10 ++
 tests/unit/test_arch.py       | 168 ++++++++++++++++++++
 tickets.md                    | 100 +++++++++++-
 6 files changed, 678 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestForkPoolHazards::test_pool_inside_pool_fires_on_process_pool_alongside_thread_pool` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestForkPoolHazards::test_pool_inside_pool_discharges_on_real_repo_run_combined_jobs` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestForkPoolHazards::test_fork_after_threads_fires_when_fork_follows_thread_start` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestForkPoolHazards::test_fork_before_threads_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestForkPoolHazards::test_pipe_wait_deadlock_fires_without_communicate` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestForkPoolHazards::test_pipe_wait_deadlock_does_not_fire_with_communicate` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestForkPoolHazards::test_self_join_deadlock_fires_when_dispatched_task_joins_its_pool` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestForkPoolHazards::test_self_join_deadlock_does_not_fire_on_undispatched_join` (pytest node id, verified passing when recorded)
