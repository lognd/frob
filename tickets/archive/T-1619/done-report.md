## Done report

A land had no exclusive lease against any OTHER ledger-writing verb, so
`frob ticket new`'s ledger auto-commit (T-1130) could move `root`'s tip
mid-land, tripping `_verified_reset_root`'s drift refusal (T-0907) and
leaving a staged REL001 bump with no disclosure of what was left behind.

Fixed:

- `refuse_if_land_in_progress` (`frob.tickets._leases`) probes the same
  `land.lock` `frob ticket land` holds (`LAND_LOCK_REL`, now the single
  home for that path constant, imported by `_land.py`) with a
  non-blocking `flock` acquire-then-release attempt. Wired into
  `_add_and_commit_tickets_md`, the single choke point
  `commit_ticket_ledger_change`/`commit_start_transition` both funnel
  through -- so `new`/`close`/`drop`/`fail`/`requeue`/`block`/`start`/
  `evidence`/`done-report` are all covered by this one guard.
- Crash-safe with no timeout: a POSIX `flock` is released by the kernel
  the instant its holder exits (any means, including SIGKILL), so a
  probe-and-release is already a trustworthy liveness check -- no
  polling, no TTL, reusing the primitive's own guarantee rather than a
  second liveness layer.
- Belt-and-braces (added per mid-task correction from the repo owner,
  folding in logic that had been living in a coordinator-side shell
  wrapper): `_scan_for_live_land_process` backstops the flock probe with
  a `/proc`-based scan for a live `frob ticket land` process against
  `root` (argv contains "ticket"+"land", cwd == root), catching the race
  window before a land acquires its lock and the fcntl-unavailable-
  platform case. Degrades to a silent no-op on any non-Linux platform or
  scan failure -- never blocks a real command over an inability to scan.
- `_verified_reset_root`'s drift-guard refusal now runs `git status
  --porcelain` and lists every path left staged/uncommitted instead of
  only pointing at "inspect by hand".
- `frob ticket land --retire-on-proof` (also from the mid-task
  correction): `--finish`'s verified-LAND-PROOF gate (commit
  is-ancestor-of-main, ticket state on main is done/dropped) plus branch
  deletion, sharing the identical gate/refusal path -- makes the unsafe
  `land && git worktree remove` two-step (which destroyed a worktree
  after a FAILED land in the reported incident, recoverable only because
  git kept the dangling commit) structurally unavailable: `_land`'s own
  `sys.exit(1)` on a failed `land()` returns before the finish/retire
  tail is ever reached, so there is no path from a failed land to either
  the worktree or its branch being touched.

Disclosed cut: T-1618 (whole-branch passenger-ticket leakage) is a
separate ticket in this same dispatch and is being worked next, not
folded into this one -- its scope (`_check_cross_ticket_leakage`/
`_land_merge.py`) is disjoint from T-1619's.

### Changed
```
 docs/modules/tickets.md                    | 130 ++++++++++++++++
 src/frob/_cli_parsers/_ticket/_progress.py |  16 ++
 src/frob/app/_config_external.py           |   2 +
 src/frob/app/config.py                     |   8 +
 src/frob/app/ticket_runner/_land_cmd.py    | 104 ++++++++++++-
 src/frob/tickets/_land.py                  |  41 ++++-
 src/frob/tickets/_land_git_ops.py          |  28 +++-
 src/frob/tickets/_leases.py                | 240 ++++++++++++++++++++++++++++-
 tests/test_ticket_leases.py                | 185 ++++++++++++++++++++++
 tests/test_ticket_work_and_land_finish.py  |  86 +++++++++++
 tickets.md                                 |  25 ++-
 11 files changed, 845 insertions(+), 20 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_allows_when_no_lock_file` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_refuses_while_land_lock_held` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_allows_after_a_killed_lands_lock_is_os_released` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_belt_and_braces_process_scan_without_the_lock_file` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_concurrent_land_and_ticket_new_cannot_corrupt_the_ledger` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_retire_on_proof_removes_worktree_and_deletes_its_branch` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_worktree_branch_name_returns_none_for_an_unregistered_path` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_delete_worktree_branch_is_a_logged_no_op_for_none` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_retire_on_proof_refuses_and_touches_nothing_when_unverified` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 0 error(s), 8375 warning(s), 712 waived
- error-findings: none (measured, zero errors)
