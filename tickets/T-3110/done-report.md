## Done report

Added `tests/test_refactor_corpus.py`: one fixture repo combining every
call-site shape T-3066/T-3105/T-3109 needed real scale to surface --
a function-local import, a `TYPE_CHECKING`-guarded import, a
`try`/`except ImportError`-guarded import, an import nested several
blocks deep, a from-import line naming both a moved and an untouched
symbol, a many-name re-export line (the `gates/__init__.py` shape), a
relative import of the source module, an aliased import, and a
`tickets/<id>/ticket.md` structured evidence citation -- exercised by
one real `run_split` (mirroring T-3086's real target shape: several
symbols moved out of a heavily-imported module, the rest left behind).
The corpus asserts the WHOLE tree stays parseable afterward, not just
the plan's own touched files -- the exact minimum bar T-3105 failed
while reporting `success=True`.

Demonstrated catch of all three known defects (checked locally, never
committed): reverted each fix's exact `_scan.py` diff in turn and
reran the corpus --
  - T-3109's fix reverted: corpus fails with 4 files losing indentation
    ("expected an indented block") -- the identical repro shape.
  - T-3105's fix reverted: corpus fails, caught by
    `verify_import_resolution`'s local-name check (`kept_c` not defined
    in the destination module) -- an even earlier catch than T-3105's
    original `success=True` escape, because a later hardening of that
    check (landed alongside T-3105's own fix) closed that gap too.
  - T-3066's fix reverted (old `ast.walk`-based
    `_shares_line_with_sibling_statement`): corpus fails -- every
    nested import misclassified as semicolon-joined, split reports 1
    unresolved reference and never rewrites the function-local caller.
Each revert-then-restore left the working tree clean; no permanent
change to src/frob/refactor/_scan.py was made or committed by this
ticket (T-3110's scope is test-only).

Fourth defect: none found while building or exercising the corpus
against the current (fixed) code.

Post-apply import check: NOT added to production code -- out of
T-3110's declared scope (tests/test_refactor_corpus.py only). Filed as
a follow-up instead (see Filed below), since `verify_import_resolution`
only checks the plan's own touched-files list, not the whole tree, and
this is exactly the gap T-3105 exploited.

Evidence:
- tests/test_refactor_corpus.py::TestRefactorCorpus::test_split_moves_symbols_across_every_call_site_shape

Filed: T-draft-561192d7 (auto-renumbered on land), titled "frob refactor
verbs' Verify phase never checks import breakage outside the plan's own
touched files" -- the unconditional whole-tree post-apply import check
this ticket's brief asked to "consider", scoped to
src/frob/refactor/_commit.py and src/frob/refactor/_verify.py.

Gates: frob check --ticket T-3110 clean (0 errors scoped to
tests/test_refactor_corpus.py; 3 pre-existing-pattern DUP001 notes
waived following test_refactor.py's own precedent for the shared
git-fixture helper shape; 1 FMT001 line-length warning fixed via
`frob fmt`).

### Changed
```
 tests/test_refactor_corpus.py      | 304 +++++++++++++++++++++++++++++++++++++
 tickets/T-3110/done-report.md      |  73 +++++++++
 tickets/T-3110/ticket.md           |   4 +-
 tickets/T-draft-561192d7/ticket.md |  54 +++++++
 4 files changed, 434 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_refactor_corpus.py::TestRefactorCorpus::test_split_moves_symbols_across_every_call_site_shape` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 94 error(s), 665 warning(s), 865 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC006@tickets/T-3110/ticket.md, DOC006@tickets/T-3115/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bp/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3110, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_land_compose.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@tests/test_ci_report.py, SUPPRESS001@tests/test_tickets.py, SUPPRESS001@tests/test_tickets_acceptance.py, SUPPRESS001@tests/test_tickets_brief.py, SUPPRESS001@tests/test_tickets_velocity.py, SUPPRESS001@tests/unit/verify/test_backpressure.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/unit/test_main_entry.py
