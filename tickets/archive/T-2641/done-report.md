## Done report

Changed:
- deleted changelog.d/T-2593.md (stray fragment for a DROPPED, not DONE, ticket)
- tests/test_release.py::TestNoStrayFragmentForNonDoneTicket.test_every_changelog_fragment_belongs_to_a_done_ticket (new repro)

Evidence:
- tests/test_release.py::TestNoStrayFragmentForNonDoneTicket.test_every_changelog_fragment_belongs_to_a_done_ticket
  (designated repro; FAILED_AT_PARENT verified against commit 7dc6c45e1, the test-only commit before deleting
  the stray fragment)

Confirmed before deleting:
- T-2615's generator fix is in place (src/frob/release/_fragments.py::write_changelog_fragment re-checks the
  ticket's CURRENT state and refuses for a non-DONE ticket at write time), so this cleanup removes residue,
  not a live bug.
- CHANGELOG.md's own T-2593 line carries no duplicated-id defect (single, correctly-formed bullet) -- per
  T-2615's own Done report policy against retroactively rewriting released notes, it is left as-is. Only the
  stray fragment file is removed.

Filed: none -- no out-of-scope work found.

Gates: `uv run pytest tests/test_release.py -k "TestChangelogFragments or TestNoStrayFragmentForNonDoneTicket"`
-> 13 passed, 0 failed. changelog.d/T-2593.md deletion committed with FROB_LAND_INTERNAL=1 (the T-2445
land-owned-artifact guard's documented escape hatch) since this ticket's entire scope IS that land-owned
file; the test-file commit needed no such escape.

### Changed
```
 changelog.d/T-2593.md    |  2 --
 tests/test_release.py    | 40 ++++++++++++++++++++++++++++++++++++++++
 tickets/T-2641/ticket.md | 13 +++++++++++--
 3 files changed, 51 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_release.py::TestNoStrayFragmentForNonDoneTicket::test_every_changelog_fragment_belongs_to_a_done_ticket` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@scripts/fleet_status.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2641, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WAIVE006@src/frob/gates/__init__.py, WAIVE006@src/frob/gates/_coverage.py, WAIVE006@src/frob/gates/_decisions_compliance.py, WAIVE006@src/frob/gates/_doclink_docanchor.py, WAIVE006@src/frob/gates/_mutation_evidence.py, WAIVE006@src/frob/gates/_sys.py, WAIVE006@src/frob/gates/_tickets_gate.py, WAIVE006@src/frob/gates/_todo_fmt.py, WAIVE006@src/frob/tickets/_draft_finalize.py, WAIVE006@src/frob/tickets/_evidence.py, WAIVE006@src/frob/tickets/_models.py, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
