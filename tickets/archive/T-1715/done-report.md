## Done report

Fix: `_finish_worktree` (the `--finish`/`--retire-on-proof` worktree
removal half of `frob ticket land`) now refuses to remove a worktree it
cannot prove is dead, instead of trusting the LAND-PROOF `verified` gate
alone. Two liveness signals, both reused from existing machinery per the
ticket's explicit instruction not to write a second scanner:

- `scan_for_live_worktree_process(path)` (new, `frob.tickets._leases`)
  generalizes T-1619's `_scan_for_live_land_process` `/proc` walk to find
  ANY live process cwd'd into `path`, not just a `frob ticket land`
  process cwd'd into the primary checkout.
- `_live_lease_for_worktree` (factored out of `_sweep_verdict_for_worktree`,
  now shared with T-1739) answers whether a live cross-worktree lease is
  still pinned to the worktree.

`refuse_if_worktree_in_use(root, worktree)` combines both into one
`Result`, logging the pid or the pinning ticket id at ERROR before
returning -- never a refusal without naming its own cause. `_finish_
worktree` calls it before `git worktree remove` and `sys.exit(1)`s on a
refusal without unwinding the (already-succeeded) land itself. `--force`
(new CLI flag, threaded to `cfg.ticket_force`, the same field `frob
ticket archive --force` already uses) overrides the guard for a worktree
independently confirmed genuinely wedged.

docs/modules/tickets.md gained a new "Worktree liveness scan (T-1715,
T-1739)" section documenting both incidents and the shared mechanism;
docs/modules/app.md's runner summary got a one-line pointer update for
T-1739's own CLI surface change (worktree_runner.py is shared scope with
the sibling ticket).

### Changed
```
 tickets.md | 42 ++++++++++++++++++++++++++++++++++++++----
 1 file changed, 38 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_land_finish_guard.py::TestScanForLiveWorktreeProcess::test_finds_a_process_cwd_into_the_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestScanForLiveWorktreeProcess::test_none_when_no_process_matches` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestLiveLeaseForWorktree::test_finds_a_live_lease_pinned_to_the_worktree` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestLiveLeaseForWorktree::test_expired_lease_is_not_live` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestRefuseIfWorktreeInUse::test_refuses_on_a_live_process_and_names_the_pid` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestRefuseIfWorktreeInUse::test_refuses_on_a_live_lease` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestRefuseIfWorktreeInUse::test_allows_when_neither_signal_fires` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestFinishWorktree::test_refuses_to_remove_a_worktree_a_live_process_is_cwd_into` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestFinishWorktree::test_removes_a_worktree_with_no_live_process` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestFinishWorktree::test_force_removes_despite_a_live_process` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestForceFlagParsing::test_force_flag_sets_the_namespace_dest` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestForceFlagParsing::test_force_defaults_false` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: 5 error(s), 556 warning(s), 724 waived
- error-findings: ARCH001@src/frob/tickets/_leases.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, DUP001@tests/unit/test_land_finish_guard.py, SELFAUDIT001@design, WIRE001@tests/unit/test_land_finish_guard.py
