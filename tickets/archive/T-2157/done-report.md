## Done report

Traced the actual mutation site (the coordinator's original scope,
src/frob/tickets/_land_git_ops.py alone, was a guess): the
`git merge --squash --no-commit` that stages a land's squash-merge
directly into the SHARED ROOT's real index/working tree -- the operation
whose SIGKILL-during-merge leaves the DirtyMain residue this ticket is
about -- runs in `_squash_and_splice_ledger`/`_squash_and_splice_ledger_v2`
in src/frob/tickets/_land_squash.py. Widened scope to include that file
(reason recorded via `frob ticket scope --add --reason-file`), plus a new
dedicated test file to avoid the test_ticket_land.py lease collision with
T-2114/T-2118.

DID NOT implement the full GIT_INDEX_FILE private-index rewrite the
ticket's "promising direction" describes: that would require moving gate
re-verification off root's own working tree entirely, and the call sites
that orchestrate WHEN/WHERE that verification runs live in
src/frob/tickets/_land.py, which this ticket does not hold (T-2155 held
it, then closed it; either way, out of this ticket's declared scope).
Recording this explicitly so the next ticket does not have to re-derive
it: the eventual full fix is to run squash+splice+verify entirely in a
scratch worktree sharing root's object store, and only touch root's real
checkout via one atomic step at the very end.

What WAS implemented, fully within the two files this ticket holds:
`reclaim_orphaned_squash_residue(root, ticket_id)` in _land_git_ops.py.
Design: reuses frob.tickets._land's EXISTING land.lock advisory flock
(T-1515, imported read-only via its path constant LAND_LOCK_REL from
frob.tickets._leases -- the single home T-1619 already established for
that path, never a second copy) as the liveness oracle, rather than
recording/comparing a pid (pid-reuse-unsafe in both directions, per the
coordinator's explicit caveat on this ticket) or inventing a competing
lock file. Every squash-merge onto root already runs strictly inside
_land_lock's critical section, so a fresh NON-BLOCKING flock acquisition
on that exact lock file proves, rather than guesses, whether root's
current staged/dirty content belongs to a live process (acquisition
fails -- touch nothing) or a dead one (acquisition succeeds -- the OS
already freed a SIGKILL'd holder's flock instantly, so success is
conclusive, not a race) -- then unwinds via the pre-existing
_verified_reset_root (T-0907's own safe-reset primitive, already used
for graceful-failure unwinds, now also reachable for the
process-died-ungracefully case this ticket is about).

NOT yet wired into land()'s own startup sequence (before land's
_refuse_if_main_dirty DirtyMain check) -- that wiring belongs in
frob.tickets._land, out of this ticket's scope. Documented as a
follow-up in the function's own docstring rather than silently leaving
it unmentioned.

Verified (BUG002 repro discipline, playbook 0.6): repro test committed
ALONE first (1657f978b), confirmed FAILING there --
`frob ticket evidence T-2157 --check-repro ... --base-ref 1657f978b` ->
FAILED_AT_PARENT (a real repro, not confirmatory-only) -- then the fix
committed separately (09a3e7d10), confirmed the same test now passes:
`pytest tests/unit/test_land_squash_residue_reclaim.py` ->
SUITE-RESULT: exitstatus=0 collected=3 failed=0, 3 passed. Designated
the repro test via --designate-repro (validated FAILED_AT_PARENT at
designate time). `frob check --only lint --json --ticket T-2157` shows
zero findings for either changed file; the one pre-existing "would
reformat" flag on the new test file matches 115 other already-noisy
files repo-wide (a frob-fmt-directive-preservation vs raw-ruff-format
disagreement that predates this ticket) and is not a regression --
`frob fmt --check` (the repo's own authoritative tool) reports it clean.

### Changed
```
 src/frob/tickets/_land_git_ops.py              | 116 ++++++++++++++++++++
 tests/unit/test_land_squash_residue_reclaim.py | 131 +++++++++++++++++++++++
 tickets/T-2157/ticket.md                       | 142 ++++++++++++++++++++++++-
 3 files changed, 387 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_reclaims_when_no_live_land_holds_the_lock` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_does_not_touch_a_live_lands_own_staging` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_clean_root_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/tickets/_land_git_ops.py, COV001@src/frob/tickets/_land_git_ops.py, DUP001@tests/unit/test_land_squash_residue_reclaim.py, PRE001@tickets/T-2157, SELFAUDIT001@design, TEST001@src/frob/tickets/_land_git_ops.py, TICK004@tickets.md, WIRE001@src/frob/tickets/_land_git_ops.py
