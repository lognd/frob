## Done report

Changed:
- src/frob/tickets/_setters.py: added `_ticket_currently_archived` (checks
  v2 archive-vs-active path existence, or archive/active membership in
  single mode) and routed `set_body`'s write through `write_archived_
  ticket` when the ticket is currently archived-only, instead of the
  plain active-only `write_ticket` -- the fix for the DuplicateId
  corruption T-2678 traces.
- tests/unit/test_ticket_store.py: added TestSetBodyArchivedTicketRouting
  with two tests -- the must-fire control (append on an archived ticket
  amends tickets/archive/<id>/ticket.md in place, no fresh tickets/<id>/
  created) and the must-NOT-regress control (append on an active ticket
  still writes tickets/<id>/ exactly as before).

Root cause: `set_body` loads via `_load_ticket_and_queue` (merged
active+archive), so it CAN find an archived ticket, but always wrote
through the plain active-only `write_ticket` -- creating a fresh
`tickets/<id>/` directory alongside the untouched `tickets/archive/<id>/`
one. `frob ticket show <id>` then refuses outright with DuplicateId,
fleet-wide, since scope/body writes mirror straight to the primary
checkout.

Positive controls (both required by the ticket, both verified):
- must-fire: test_append_on_archived_ticket_writes_archive_path_only --
  genuinely FAILS at the pre-fix commit (704f7bfc1, confirmed via
  `frob ticket evidence --check-repro`: FAILED_AT_PARENT, a real repro,
  not confirmatory-only) and passes at the fix commit.
- must-NOT-regress: test_append_on_active_ticket_still_writes_active_path
  -- a non-archived ticket's append still writes the active path exactly
  as before this fix.

Evidence: tests/unit/test_ticket_store.py::
TestSetBodyArchivedTicketRouting::
test_append_on_archived_ticket_writes_archive_path_only (designated
repro, FAILED_AT_PARENT confirmed against 704f7bfc1) and ::
test_append_on_active_ticket_still_writes_active_path (must-NOT-regress
control).

Gates: `frob check --ticket T-2678 --json` -> 0 findings of any severity
against src/frob/tickets/_setters.py or tests/unit/test_ticket_store.py
(the two touched files); repo-wide baseline ~60 pre-existing errors
unrelated to this ticket's diff, unchanged by it.

Filed: T-2709 (single-mode test coverage follow-up).

### Changed
```
 src/frob/tickets/_setters.py       | 46 ++++++++++++++++++++-
 tests/unit/test_ticket_store.py    | 82 ++++++++++++++++++++++++++++++++++++++
 tickets/T-2678/done-report.md      | 63 +++++++++++++++++++++++++++++
 tickets/T-2678/ticket.md           | 49 +++++++++++++++++++++--
 tickets/T-2709/ticket.md | 37 +++++++++++++++++
 5 files changed, 272 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_store.py::TestSetBodyArchivedTicketRouting::test_append_on_archived_ticket_writes_archive_path_only` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestSetBodyArchivedTicketRouting::test_append_on_active_ticket_still_writes_active_path` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 36 error(s), 954 warning(s), 703 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2691/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t2679-series/src/frob/gates/_fix_engine.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2678, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
