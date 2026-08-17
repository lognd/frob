## Done report

Changed:
- src/frob/tickets/_land_squash.py::_record_land_commit (git add -A -> pathspec-scoped delta-based add)
- src/frob/tickets/_land_finalize.py::_land_finalize_and_close (snapshots dirty paths before finalize writes)
- src/frob/tickets/_land_finalize.py::_commit_finalize_writes (git add -A -> pathspec-scoped delta-based add, before_dirty param)
- src/frob/tickets/_land.py::_land_plan_merge_and_finalize (snapshots dirty paths before finalize writes)
- src/frob/tickets/_land.py::_land_plan_commit_finalize (git add -A -> pathspec-scoped delta-based add, before_dirty param)
- src/frob/tickets/_land_git_ops.py::_pathspec_targets (new: makes a porcelain-status delta safe to hand to `git add --`, since a rename/copy entry renders as "old -> new")

Mechanism: each of the three bookkeeping-commit sites snapshots
`_porcelain_dirty_paths(root)` immediately BEFORE the write it is
responsible for, then computes the same set again AFTER; only the delta
(paths that became dirty as a direct result of THIS step's own write) is
passed to `git add --`, never `git add -A`. This is mode-agnostic (works
whatever storage shape the underlying write touches) and structurally
excludes a bystander's dirty file that was already sitting in the shared
root before this step ran -- the exact shape of the T-2256 incident named
in this ticket -- while still committing everything this step legitimately
owns, however many files that turns out to be.

Detection note (per the coordinator's ask, not implemented here -- out of
this ticket's declared scope): a land-time import-check of any Python
module a land-owned bookkeeping commit touches (compile/AST-parse each
touched .py file's new blob for undefined names is not generally possible
statically without full type inference, but a cheap post-commit
`python -c "import <module>"` smoke pass, or wiring `_porcelain_dirty_paths`
itself into a WARNING when a bookkeeping-commit step's delta unexpectedly
includes a path outside a small allowlist for that step) would have
caught this specific incident (a NameError on first real use) well before
every land started crashing. Not filed as a follow-up ticket since it is
a genuine net-new capability, not a bug in existing code -- left as a
note per the coordinator's explicit ask rather than a silent omission.

Evidence:
- tests/test_ticket_land.py::TestRecordLandCommit::test_record_land_commit_never_absorbs_a_bystanders_dirty_file (designated repro, FAILED_AT_PARENT verified against commit 972e60fd2 -- the repro-test-only commit, before the fix commit f65ef242d)

Pre-existing failures (NOT caused by this change, confirmed by reverting
this ticket's diff and re-running against unmodified main 78d33cbd8):
- TestLand::test_refuses_on_dirty_main
- TestLedgerV2LandMergeStory::test_same_ticket_conflict_surfaces_loudly_no_splice
- TestUvLockSync::test_dirty_lock_with_other_change_still_refuses
- TestUvLockSync::test_dirty_lock_version_plus_other_line_still_refuses
Filed as T-2283 (renumbers to a real id at its own land) -- not investigated/fixed here because isolating
them is a distinct investigation outside T-2274's own scope; flagging
here so they are not mistaken for a regression this ticket introduced.

Gates: full tests/test_ticket_land.py run is 276 passed, 4 failed (the
pre-existing failures above) both before and after this change -- byte-
identical failure set, confirmed via a revert/re-run/reapply cycle.

### Changed
```
 src/frob/tickets/_land.py          | 33 +++++++++++++++++++++++-----
 src/frob/tickets/_land_finalize.py | 38 +++++++++++++++++++++++++++-----
 src/frob/tickets/_land_git_ops.py  | 22 +++++++++++++++++++
 src/frob/tickets/_land_squash.py   | 33 +++++++++++++++++++++++++++-
 tests/test_ticket_land.py          | 44 ++++++++++++++++++++++++++++++++++++++
 tickets/T-2274/ticket.md           | 14 ++++++++----
 tickets/T-2283/ticket.md | 40 ++++++++++++++++++++++++++++++++++
 7 files changed, 209 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestRecordLandCommit::test_record_land_commit_never_absorbs_a_bystanders_dirty_file` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH001@src/frob/tickets/_land_finalize.py, ARCH001@src/frob/tickets/_land_squash.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2274/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2274/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2274/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2274/tests/test_ticket_land.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2274, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
