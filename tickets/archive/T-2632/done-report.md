## Done report

Changed: tests/unit/test_mutation_sweep_queue.py::_make_ticket, tests/unit/test_mutation_sweep_queue.py::TestPendingSweepCount.test_counts_only_pending_entries

Root cause: the T-1995 duplicate-title guard (`_new_renumber.py`'s "refusing
to file '<title>' -- already has this exact title and this exact scope")
correctly refuses a second `new_ticket` call with an identical title+scope.
`test_counts_only_pending_entries` calls the file's own `_make_ticket`
helper twice with the hardcoded title "seed" and no scope, so the second
call is a genuine duplicate and the guard fires as designed -- a stale test
fixture, not a production defect. Same class of finding as T-2602's
documented precedent (this repo's own guard, its own fixture, updated to
comply).

Fix: gave `_make_ticket` an overridable `title` keyword (default "seed",
unchanged for every other call site in the file that only seeds one
ticket), and passed distinct titles ("seed-a"/"seed-b") at the one call
site that seeds two tickets in the same tmp_path.

Evidence: tests/unit/test_mutation_sweep_queue.py::TestPendingSweepCount::test_counts_only_pending_entries
(designated repro, FAILED_AT_PARENT at e46bc39b85215ed0825179d79f035122dad0de65)

Positive controls: full file (6 tests) passes after fix. Deliberately
reverted ticket_b's title back to "seed-a" (same as ticket_a) and confirmed
the test fails again with the real DuplicateTicket AssertionError before
correcting it back to "seed-b".

Filed: none

Gates: uv run frob check --ticket T-2632 (see log; unrelated repo-wide
findings only, no findings inside this ticket's scope); designated repro
FAILED_AT_PARENT confirmed via --check-repro

### Changed
```
 tickets/T-2632/ticket.md | 8 ++++++--
 1 file changed, 6 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_mutation_sweep_queue.py::TestPendingSweepCount::test_counts_only_pending_entries` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@scripts/fleet_status.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2632, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WAIVE006@src/frob/gates/__init__.py, WAIVE006@src/frob/gates/_coverage.py, WAIVE006@src/frob/gates/_decisions_compliance.py, WAIVE006@src/frob/gates/_doclink_docanchor.py, WAIVE006@src/frob/gates/_mutation_evidence.py, WAIVE006@src/frob/gates/_sys.py, WAIVE006@src/frob/gates/_tickets_gate.py, WAIVE006@src/frob/gates/_todo_fmt.py, WAIVE006@src/frob/tickets/_draft_finalize.py, WAIVE006@src/frob/tickets/_evidence.py, WAIVE006@src/frob/tickets/_models.py, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
