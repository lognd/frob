## Done report

## Done report

Changed (round 2, reviewer fix): reviewer REJECTed round 1 on one blocking
finding -- mutate's refusal-as-killed made mutation score gameable via
FROB_DISABLE_EXEC=1 (fabricated 100% score / zero survivors without
running a test). Fixed:

- src/frob/mutate/__init__.py: new `MutateError.ExecDisabled` variant.
  `_run_mutants` now returns `Result[tuple[int, list[Mutant]], MutateError]`
  and returns `Err(MutateError.ExecDisabled)` on the FIRST guarded refusal,
  aborting the whole run instead of scoring it killed (the TimeoutExpired
  case is left as "killed" -- that IS observed behavior under the mutant;
  a refusal ran nothing). `run_mutations` propagates the `Err`, still
  restores the source file (existing `finally`), and logs the abort
  reason. `frob.app.mutate_runner.run` already logs `result.danger_err`
  and exits nonzero on `Err` -- no runner change needed.
- tests/test_mutate.py::test_run_mutations_kill_switch_refuses_without_spawning:
  kept the spy-no-spawn assertion, changed expectation from
  `result.is_ok`/no-survivors/100% to `result.is_err` /
  `MutateError.ExecDisabled`.

Evidence (round 2): `uv run --frozen pytest tests/test_mutate.py -q`
(11 passed) and `tests/unit/test_app_runners.py -k "Mutate or mutate"`
(6 passed, mutate_runner CLI wiring incl. its own Err-exits-1 path).
`uv run --frozen frob test --base main` exit=0 (python selection).
`uv run --frozen frob check --ticket T-0803` chunked (lint, gates-fast)
re-run PASS, 0 errors, after `frob ticket sweep T-0803` refreshed the
pre-work stamp. Deletion filter (`git diff main --diff-filter=D`) empty.

All other 10 sites/contracts/tests from round 1 stand as reviewed sound
(unchanged this round). The gitlog human-mode DEBUG-loss nit and the
--json sweep are explicitly out of this ticket's scope per reviewer/
coordinator direction (coordinator filing its own ticket for the sweep).

Filed: none.

Gates: `uv run --frozen frob check --ticket T-0803` chunked loop clean,
0 errors, after both rounds' sweeps. No waivers added.

Worktree: /home/logan/projects/frob/.claude/worktrees/agent-a39110485a411b302
Commits (round 2 adds one on top of round 1's three):
- 90a5a8cf fix(process): wire remaining subprocess call sites through T-0778 exec guard
- 849e55d2 Merge branch 'main' into worktree-agent-a39110485a411b302
- 5d5b5b6d chore(tickets): record T-0803 Done report (round 1)
- e015d4fd fix(mutate): abort mutation run on exec-disabled instead of scoring killed

### Changed
```
 src/frob/app/gitlog_runner.py                 |  30 +++--
 src/frob/app/ticket_runner.py                 |  21 +++-
 src/frob/deploy/_vm_runner.py                 |  25 +++-
 src/frob/fleet/__init__.py                    |  22 +++-
 src/frob/gitlog/__init__.py                   |  16 ++-
 src/frob/mutate/__init__.py                   |  38 +++++-
 src/frob/scaffold/project.py                  |  25 ++--
 src/frob/testing/_coverage_wait.py            |  20 +++-
 src/frob/tickets/__init__.py                  |  23 ++--
 src/frob/tickets/clipboard.py                 |  56 +++++++--
 tests/test_app.py                             |  35 +++++-
 tests/test_clipboard.py                       |  34 ++++++
 tests/test_mutate.py                          |  46 ++++++++
 tests/test_tickets_lease.py                   |  32 ++++++
 tests/unit/deploy/test_vm_runner.py           |  43 ++++++-
 tests/unit/fleet/test_status.py               |  45 ++++++++
 tests/unit/test_gitlog.py                     |  28 +++++
 tests/unit/test_scaffold_project.py           |  34 ++++++
 tests/unit/test_ticket_runner_land_release.py |  31 ++++-
 tickets.md                                    | 160 +++++++++++++++++++++++++-
 20 files changed, 693 insertions(+), 71 deletions(-)
```

### Evidence
- `tests/unit/test_gitlog.py::test_git_log_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestBreadthPerf::test_repo_files_git_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestLandRebuildNativesFn::test_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_status.py::TestCollectStatus::test_git_branch_and_dirty_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_status.py::TestCollectStatus::test_gate_summary_probe_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
- `tests/test_clipboard.py::TestKillSwitch::test_clipboard_image_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
- `tests/test_mutate.py::test_run_mutations_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
- `tests/unit/deploy/test_vm_runner.py::TestAvail::test_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
- `tests/unit/test_scaffold_project.py::test_hooks_dir_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
- `tests/test_app.py::TestRunCoverageWait::test_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
