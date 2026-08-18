## Done report

Wired `frob.tickets._leases.force_release_lease` into a CLI verb, per
brief. The original plan (a new `frob ticket lease release <id>`
subcommand) was stale: T-2175 had already shipped `frob worktree
release-lease` on top of `force_release_lease`'s scope-divergence path,
so the correct, non-duplicative fix is `--force --reason` on the
EXISTING verb, not a second competing CLI surface. This targets the
real gap: the existing verb refuses (correctly) unless
`lease_staleness_reason`/T-2175's scope-divergence check confirm
staleness, with no override for a lease an operator has independently
judged abandoned that fails to match any of those shapes -- exactly the
two incidents in the brief.

Scope was widened from the ticket's filed set (AppConfig/_cli_parsers/
_ticket/**/ticket_runner __init__.py -- all blocked by T-2302's live
lease anyway) to `src/frob/app/worktree_runner.py` and
`src/frob/tickets/_leases.py`, via `frob ticket scope --reason`, twice,
both recorded in T-1777's own scope_changes audit trail.

A persisted ticket-model audit field (`_models.py`) for the
--force reason was NOT added: `src/frob/tickets/_models.py` is under
T-2302's live cross-worktree lease for the duration of this ticket, so
it could not be added to scope. The --reason is instead folded into
`force_release_lease`'s own WARNING log line (audit-by-log, not by
ledger field) -- disclosed as a cut, follow-up filed.

### Changed
```
 tickets/T-1777/ticket.md           |  9 +++++++-
 tickets/T-2333/ticket.md | 42 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 50 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_leases_cross_worktree.py::TestForceReleaseLease::test_reason_is_included_in_the_warning_log` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli::test_release_lease_cli_force_requires_reason` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli::test_release_lease_cli_force_releases_a_live_looking_lease` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, AFFECT001@src/frob/app/worktree_runner.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH001@src/frob/app/worktree_runner.py, ARCH001@src/frob/tickets/_leases.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/gates/_fmt_directives.py, DRIFT002@scripts/fleet_status.py, DRIFT002@src/frob/verify/_drain.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-1777, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK004@tickets.md, WIRE003@docs/modules/cli.md
