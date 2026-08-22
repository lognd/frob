## Done report

Fixed the two attributed findings on T-2651's fleet_status additions:

- COV001: `_resolve_worktree_for_in_progress_ticket` (scripts/fleet_status.py)
  was missing its `frob:tests` edge -- T-2651 had already written tests that
  exercise both of its branches (recorded-lease-hit via
  `TestInProgressTicketScopeLeases.test_live_worktree_named_not_leaked`,
  no-resolution-fallback via `test_no_worktree_flagged_as_leak`); no new
  test was needed, only the missing directive. `in_progress_ticket_scope_
  leases` itself already carried its own frob:tests edge -- only its
  private helper was missing one.
- DOC002: `docs/guides/coordinator-scripts.md` had two `frob:doc` pointer
  anchors (`#in_progress_ticket_scope_leases`,
  `#_resolve_worktree_for_in_progress_ticket`) with no matching sections.
  Added both, matching the surrounding module's existing per-symbol
  section depth/shape (one paragraph of WHY plus the caller-visible
  contract, referencing the T-2377 incident T-2651's own docstring cites).

Evidence is confirmatory-only: both bound tests already PASS at the
parent commit (`--check-repro` returned PASSED_AT_PARENT) because this
ticket only added a missing directive/doc anchor, not new behavior --
there is no defect a test could newly fail against. Waiving BUG002 with
that stated reason rather than fabricating a repro.

Positive controls run: `frob check --only coverage --only docanchor
--ticket T-2655 --delta` shows zero COV001/DOC002/DOC003-class findings
for scripts/fleet_status.py or docs/guides/coordinator-scripts.md; the
remaining COV/DOC/DRIFT/WAIVE errors in that run are pre-existing,
repo-wide, and unrelated to this ticket's scope (confirmed by grepping
the output for fleet_status/coordinator-scripts -- zero hits).

### Changed
```
 tickets/T-2655/ticket.md | 7 ++++++-
 1 file changed, 6 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeases::test_no_worktree_flagged_as_leak` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeases::test_live_worktree_named_not_leaked` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2655, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WAIVE006@src/frob/gates/__init__.py, WAIVE006@src/frob/gates/_coverage.py, WAIVE006@src/frob/gates/_decisions_compliance.py, WAIVE006@src/frob/gates/_doclink_docanchor.py, WAIVE006@src/frob/gates/_mutation_evidence.py, WAIVE006@src/frob/gates/_sys.py, WAIVE006@src/frob/gates/_tickets_gate.py, WAIVE006@src/frob/gates/_todo_fmt.py, WAIVE006@src/frob/tickets/_draft_finalize.py, WAIVE006@src/frob/tickets/_evidence.py, WAIVE006@src/frob/tickets/_models.py, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
