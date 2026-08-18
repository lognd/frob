## Done report

Persisted `frob worktree release-lease --force`'s operator-supplied
--reason as a ledger audit entry, per this ticket's own body (filed as
T-1777's own disclosed cut).

- Added `LeaseForceReleaseEntry` (src/frob/tickets/_models.py), mirroring
  `ScopeChangeEntry`'s (T-0455) frozen/append-only shape: reason,
  staleness_reason (None for --force, since --force only fires when none
  of lease_staleness_reason's shapes matched), actor, at.
- Added `Ticket.lease_force_releases: tuple[LeaseForceReleaseEntry, ...]`.
- `force_release_lease` (src/frob/tickets/_leases.py) now best-effort
  appends an entry via new `_record_lease_force_release_audit` whenever
  it is called WITH a reason (the CLI --force path) -- never for the
  internal reason-less call `release_orphaned_lease` makes on its own
  confirmed-stale path, matching the ticket's own scope ("--force's
  reason", not every release). Best-effort: an unresolvable ticket or a
  ledger write failure degrades to a WARNING, never turns a successful
  lease release into a reported failure -- matches this module's
  existing best-effort posture for every other side-channel write.
- Updated docs/modules/tickets-lifecycle.md and worktree_runner.py's own
  docstring to describe the new persisted half alongside the existing
  WARNING log.

Also fixed, in the same file (src/frob/tickets/_leases.py, already in
scope, discovered while adding the new frob:doc/frob:tests directives):
`force_release_lease` had NO `frob:doc`/`frob:tests` directives at all
on main (COV001/TEST001 both fired fresh on this ticket's own gate run)
-- a T-1777 land-time artifact where the old WIRE001-waiver comment
block (which had carried them) was removed but never replaced. Restored
proper frob:doc (pointing at the cross-worktree-lease-side-channel
section) and frob:tests (the 5 real tests covering it, 4 pre-existing +
this ticket's own new one) directives; also removed a stray, misplaced
frob:doc/frob:tests block that had ended up on the PRIVATE
`_log_force_released` helper instead (COV007), moving that coverage
onto the public function it belongs to.

Verified with `frob check --only gates-fast --ticket T-2333`,
before/after: SCOPE001 (test file initially out of declared scope,
fixed via `scope --add`), COV001/TEST001 on force_release_lease, and
COV007 on _log_force_released all cleared; no other errors touch any of
the 4 touched files (src/frob/tickets/_models.py, src/frob/tickets/
_leases.py, src/frob/app/worktree_runner.py, tests/test_ticket_leases_
cross_worktree.py) -- every remaining FAIL (COV/DOC/PRE/RENDER/TICK) is
pre-existing repo-wide noise in unrelated files/modules.

Ran the full existing test files for everything touched:
tests/test_ticket_leases_cross_worktree.py (29 passed, 1 new) and
tests/test_ticket_leases.py (136 passed) -- 164 total, all green.

New positive-control test (TestForceReleaseLease.test_reason_is_
persisted_to_the_ticket_ledger): creates a real ticket, transitions it
in-progress, force-releases with a reason, then loads the ticket back
via `load_active` and asserts `lease_force_releases` has exactly one
entry carrying that reason -- proves the ledger write happened, not
just that the function returned Ok.

frob:no-behavior-change reason="this ticket ADDS a new field/audit-write path and does not change any existing behavior's observable output (force_release_lease still returns the same Ok/Err values, still logs the same WARNING text) -- the designated evidence test (the CLI integration test) is unaffected either way"

### Changed
```
 tickets/T-2333/ticket.md | 14 +++++++++++++-
 1 file changed, 13 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_leases_cross_worktree.py::TestForceReleaseLease::test_reason_is_persisted_to_the_ticket_ledger` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli::test_release_lease_cli_force_releases_a_live_looking_lease` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2333/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
