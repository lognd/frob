## Done report

The T-1456 post-land sweep verified AFTER land's squash-apply commit
already existed on main; a refusal required a git reset --hard, which
(as T-1495 documents) can destroy foreign commits interleaved after the
land if the reset window overlaps a concurrent land. This ticket moves
the sweep earlier, to the last checkpoint before that commit is made.

Implemented:
- land() (frob.tickets._land) gains an optional `pre_commit_sweep(root,
  final_id) -> bool | None` callback, threaded through _land_locked ->
  _land_squash_apply -> _land_squash_apply_finish, invoked via the new
  _apply_pre_commit_sweep_or_unwind helper (split out to keep
  _land_squash_apply_finish under the ARCH001 line threshold) right
  before _commit_squash_apply. At that point root's working tree holds
  only the staged, uncommitted merge-preview changeset -- a `False`
  verdict unwinds via the SAME _verified_reset_root path every other
  pre-commit failure (bump_version, sync_gate_rules, completeness) already
  uses, so the refusal costs nothing and touches no real commit. A new
  LandError.PreLandUnscopedSweepFailed names this refusal.
- The CLI (_land_cmd.py) wires this in: _pre_commit_unscoped_error_sweep
  is the pre-commit twin of _post_land_unscoped_error_sweep (same
  identity-set diff + Tier-A-retry logic), and
  _sweep_apply_tier_a_pre_commit is its Tier-A-fix-then-STAGE helper
  (never commits -- the fix belongs in the same final commit, not a
  separate follow-up one, unlike the post-land twin which must commit
  separately since main already has a real commit by the time it runs).
  _land_pre_commit_sweep_fn is the closure `_land()` passes as
  `pre_commit_sweep`; it reuses the SAME T-1463 background baseline
  thread/result the post-land sweep also consumes (joins it, which is
  almost always already finished by this late in land()'s own
  sequential work) -- no second baseline scan.
- The T-1456 post-land sweep (_run_post_land_sweep_or_exit) is
  unchanged, left wired in as a cheap final assertion for whatever the
  pre-commit pass could not see (e.g. a ledger-splice-only artifact).

Tests added:
- tests/test_ticket_land.py::TestPreCommitUnscopedSweep -- land()-level,
  real git: true/None/no-callback verdicts land normally, a False
  verdict unwinds to the pre-land sha with an empty git status and
  commits nothing.
- tests/test_ticket_work_and_land_finish.py::TestPreCommitUnscopedSweepFn
  -- unit-level (monkeypatched _unscoped_error_findings/
  _sweep_apply_tier_a_pre_commit): None baseline/fresh is a skip (not a
  pass), no new finding is True, a new finding Tier-A resolves and
  stages (never commits) is True, an unresolved new finding is False.

Also added the `attr interface=TestPreCommitUnscopedSweep;` /
`TestPreCommitUnscopedSweepFn;` declarations to design/frob.strata's
`testsuite` node (SELFAUDIT001/SYS104) and `frob:ticket T-1514` edges on
the new/changed test symbols (COV002).

### Changed
```
 design/frob.strata                        |   3 +
 src/frob/app/ticket_runner/_land_cmd.py   | 249 ++++++++++++++++++++++++++----
 src/frob/tickets/_land.py                 |  17 +-
 src/frob/tickets/_land_squash.py          |  57 ++++++-
 src/frob/tickets/_models.py               |   9 ++
 tests/test_ticket_land.py                 |  81 ++++++++++
 tests/test_ticket_work_and_land_finish.py | 159 ++++++++++++++++++-
 tickets.md                                |  63 +++++++-
 8 files changed, 599 insertions(+), 39 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestPreCommitUnscopedSweep::test_true_verdict_lands_normally` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestPreCommitUnscopedSweep::test_none_verdict_is_a_skip_lands_normally` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestPreCommitUnscopedSweep::test_false_verdict_unwinds_and_commits_nothing` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestPreCommitUnscopedSweep::test_no_callback_is_noop` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestPreCommitUnscopedSweepFn::test_new_finding_fixed_by_tier_a_stages_and_returns_true` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestPreCommitUnscopedSweepFn::test_new_finding_unresolved_by_tier_a_returns_false` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 3 error(s), 134 warning(s), 779 waived
- error-findings: AFFECT001@src/frob/tickets/_land.py, AFFECT001@src/frob/tickets/_models.py, DOC002@src/frob/app/ticket_runner/_land_cmd.py
