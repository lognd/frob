## Done report

Added `_cross_ticket_carried_paths` and wired it into
`_warn_land_override_flags` in `src/frob/app/ticket_runner/_land_cmd.py`:
when `--allow-cross-ticket` is set, the land now logs the FULL set of
touched files that fall outside the landing ticket's own declared scope,
before the land proceeds. This is deliberately broader than
`CrossTicketLeakage`'s own `leaked` reporting, which only names files
colliding with ANOTHER open ticket's declared scope -- a passenger file
with no scope owner at all (a stray doc-directive citation, an untracked
edit) was previously invisible until a manual post-land `git show
--stat`. `None` is returned (and disclosed as "could not compute", never
as an empty set) whenever the touched-file diff or the ticket itself
cannot be loaded, so an unmeasurable case can never read as "nothing
carried".

Positive/negative controls: a planted out-of-scope file is reported
carried; an all-in-scope touched set reports nothing carried; an
unmeasurable diff (`None` in) and an unloadable ticket both return `None`
rather than a false empty set; the log-visible warning only fires when
`--allow-cross-ticket` is actually set (no flag, no disclosure noise).

### Changed
```
 rapid-debt.jsonl                                   |   5 +
 src/frob/app/telemetry.py                          |  14 ++
 src/frob/app/ticket_runner/_land_cmd.py            |  96 ++++++++++-
 src/frob/app/ticket_runner/_new.py                 |  10 ++
 src/frob/tickets/_land_verify.py                   |  45 ++++++
 .../test_land_verify_claim_divergence_sentinel.py  | 118 ++++++++++++++
 tests/unit/test_ticket_runner_land_cmd_flags.py    | 177 +++++++++++++++++++++
 tickets/T-1549/done-report.md                      |  63 ++++++++
 tickets/T-2141/done-report.md                      |  42 +++++
 tickets/T-2141/ticket.md                           |  16 +-
 tickets/T-2303/done-report.md                      |  84 ++++++++++
 tickets/T-2303/ticket.md                           |   9 +-
 tickets/T-2691/ticket.md                 |  58 +++++++
 tickets/T-2692/ticket.md                 |  42 +++++
 14 files changed, 774 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestCrossTicketCarriedPathsDisclosure::test_out_of_scope_file_is_reported_carried` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestCrossTicketCarriedPathsDisclosure::test_all_files_in_scope_reports_nothing_carried` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestCrossTicketCarriedPathsDisclosure::test_none_touched_paths_is_unmeasurable_not_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestCrossTicketCarriedPathsDisclosure::test_unloadable_ticket_returns_none_not_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestWarnLandOverrideFlagsDisclosesCarriedSet::test_carried_file_is_logged_at_warning` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestWarnLandOverrideFlagsDisclosesCarriedSet::test_no_flag_no_disclosure_logged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 34 error(s), 875 warning(s), 700 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2691/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
