## Done report

fleet_status's LEASES section read only `.git/frob-leases/*.json` files.
Those files are opportunistically unlinked by frob's own
`read_all_leases`/`_live_leases_pruning_stale` the moment ANY OTHER
ticket's lease scan confirms the recorded worktree path is gone -- correct
when an agent finished and its worktree was removed, but silently wrong
for a ticket that is still `in-progress` with nobody working it (blocked
and its worktree removed by hand, or abandoned). That is exactly how
T-2377 went invisible: nine hours in-progress holding
docs/modules/gates.md, its worktree gone, its lease FILE also gone, while
`frob ticket start`'s own collision check (which reads ticket state/scope
off the ledger directly, never the lease file) refused for real.

Added `in_progress_ticket_scope_leases()`: enumerates every `state:
in-progress` ticket directly off its local ledger file (the same
authoritative source `frob ticket start`'s collision check reads), then
best-effort names a worktree via the lease file (if it still resolves to
a live path) or a scope-correlated `worktrees_touching_ticket` scan.
`worktree is None` (and `leaked=True`) only when NEITHER source can name
one -- the leak signature.

`_print_fleet_report`'s LEASES section now merges this in on top of the
existing file-based `leases()` list: any in-progress ticket the file-
based list missed is printed as an extra row, tagged `[LEAK]` when no
worktree could be named, `[live]` otherwise, and the section header's
count/parenthetical now includes a leaked-count alongside the existing
live-count.

Verified against the real repo state (root checkout, not this worktree,
since a worktree's own `.git` is a file not a dir and `REPO/.git/
frob-leases` resolves wrong from inside one -- a pre-existing property of
this script, not something this ticket touches): T-2626/T-2651 (queued on
root, unlanded elsewhere) correctly do not appear; T-1686/T-2581/T-2638
(genuinely in-progress with live leases) resolve their worktree names
exactly as before.

Positive controls (all four, per the ticket's own acceptance criteria):
verified via the new unit tests -- an in-progress ticket with scope and no
resolvable worktree appears flagged leaked=True
(test_no_worktree_flagged_as_leak); an in-progress ticket with a live
lease-file worktree is named, unchanged
(test_live_worktree_named_not_leaked); a queued ticket never appears
(test_queued_ticket_excluded); the printed LEASES section correctly
merges both sources and flags the missing case
(test_leases_section_reports_ledger_leak_missing_from_held), while the
existing file-based-only case still prints exactly as before
(test_leases_section_shows_classification_per_lease, updated only for
the new header format).

Do NOT: did not touch `leases()` itself (still the raw file-based reader,
still used by `lease_classification`/`live_lease_count`/`ticket_
readiness`/`scope_intersections` -- out of this ticket's declared scope,
and none of those call sites depend on the leak case this ticket fixes).
Did not implement the "blocked yet still in-progress" flag the ticket's
own body suggested filing separately if it didn't fit cleanly -- it does
not: this ticket's fix is presence-of-worktree, not blocked-state, a
genuinely separate signal. Filed as a follow-up.

### Changed
```
 scripts/fleet_status.py                | 123 ++++++++++++++++++++++++++++++-
 tests/unit/test_coordinator_scripts.py | 127 ++++++++++++++++++++++++++++++++-
 tickets/T-2651/ticket.md               |  12 +++-
 3 files changed, 258 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeases::test_no_worktree_flagged_as_leak` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeases::test_live_worktree_named_not_leaked` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeases::test_queued_ticket_excluded` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintFleetReport::test_leases_section_shows_classification_per_lease` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintFleetReport::test_leases_section_reports_ledger_leak_missing_from_held` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@scripts/fleet_status.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@scripts/fleet_status.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, F401@/home/logan/projects/frob/.claude/worktrees/t2651-t2613/src/frob/app/ticket_runner/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2651, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
