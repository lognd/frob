## Done report

Built TDD001 (frob.gates._tdd_order): a frob:tests edge's artifact/
implementation symbol must not be introduced at or before its verifying
test's introducing commit -- the git-history half of T-3004 section 7's
TDD discipline, generalising BUG002's single-case "repro fails at parent
commit" precedent to every frob:tests binding.

Placement: pre-land, against a ticket's own worktree branch commit
sequence -- never post-land against main, since frob ticket land squashes
a ticket's commits into one and ordering becomes structurally
unobservable there (the same T-2019/T-2025 constraint BUG002 already
documents).

resolve_symbol_introduction resolves a symref's introducing commit by
scanning the file's own history oldest-first and ast.parse-ing each
revision's real content (symbol-level, not a git log -S pickaxe text
search -- corrected during this ticket after a design-audit finding that
the original pickaxe approach was lexical). classify_order compares two
introducing commits by git ancestry and reports one of three outcomes:
TEST_FIRST (silent), IMPLEMENTATION_FIRST (Severity.ERROR -- includes the
same-commit case, a determinate non-test-first fact rather than an
unknown, corrected during this ticket after a second design-audit
finding that collapsing it into UNRESOLVED would make TDD001 unable to
ever fire against the dominant squash-land workflow), and UNRESOLVED
(Severity.UNRESOLVED, T-1664's doctrine -- reserved for a genuinely
unresolvable commit or diverged histories).

Land-time wiring into frob.tickets._land (mirroring bug_repro_violations'
own call site) is deferred to T-3057, filed during this ticket
-- this ticket's scope was the check and its rule, not the call site, and
not the waterfall gate T-3004 section 9 explicitly defers.

Evidence: 18 unit tests in tests/gates/test_tdd_order.py covering all
three TDDOrder outcomes plus the ast-symbol-vs-lexical-mention
distinction, against real tiny git repos with controlled commit
sequences (never a mocked git spawn).

### Changed
```
 design/frob.strata                 |   2 +-
 docs/modules/gates.md              |  61 ++++++
 src/frob/gates/__init__.py         |  12 ++
 src/frob/gates/_tdd_order.py       | 369 +++++++++++++++++++++++++++++++++++++
 tests/gates/test_tdd_order.py      | 308 +++++++++++++++++++++++++++++++
 tickets/T-3009/ticket.md           |  60 +++++-
 tickets/T-3057/ticket.md |  45 +++++
 7 files changed, 855 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/gates/test_tdd_order.py::TestSymrefHelpers::test_symref_path_splits_on_double_colon` (pytest node id, verified passing when recorded)
- `tests/gates/test_tdd_order.py::TestSymrefHelpers::test_symref_qualname_keeps_the_full_dotted_path` (pytest node id, verified passing when recorded)
- `tests/gates/test_tdd_order.py::TestAstQualnames::test_collects_nested_dotted_qualnames` (pytest node id, verified passing when recorded)
- `tests/gates/test_tdd_order.py::TestAstQualnames::test_a_bare_mention_in_a_docstring_or_comment_is_not_a_definition` (pytest node id, verified passing when recorded)
- `tests/gates/test_tdd_order.py::TestAstQualnames::test_unparseable_source_yields_an_empty_set` (pytest node id, verified passing when recorded)
- `tests/gates/test_tdd_order.py::TestResolveSymbolIntroduction::test_resolves_the_commit_that_added_the_symbol` (pytest node id, verified passing when recorded)
- `tests/gates/test_tdd_order.py::TestResolveSymbolIntroduction::test_returns_none_for_a_symbol_never_added` (pytest node id, verified passing when recorded)
- `tests/gates/test_tdd_order.py::TestResolveSymbolIntroduction::test_a_mere_textual_mention_does_not_count_as_introduction` (pytest node id, verified passing when recorded)
- `tests/gates/test_tdd_order.py::TestClassifyOrder::test_fires_when_implementation_precedes_test` (pytest node id, verified passing when recorded)
- `tests/gates/test_tdd_order.py::TestClassifyOrder::test_stays_quiet_when_test_precedes_implementation` (pytest node id, verified passing when recorded)
- `tests/gates/test_tdd_order.py::TestClassifyOrder::test_fires_when_commits_are_identical` (pytest node id, verified passing when recorded)
- `tests/gates/test_tdd_order.py::TestClassifyOrder::test_reports_unresolved_when_either_commit_is_unresolvable` (pytest node id, verified passing when recorded)
- `tests/gates/test_tdd_order.py::TestClassifyOrder::test_reports_unresolved_on_diverged_history` (pytest node id, verified passing when recorded)
- `tests/gates/test_tdd_order.py::TestTddOrderViolations::test_fires_on_a_planted_implementation_first_pair` (pytest node id, verified passing when recorded)
- `tests/gates/test_tdd_order.py::TestTddOrderViolations::test_stays_quiet_on_a_genuine_test_first_pair` (pytest node id, verified passing when recorded)
- `tests/gates/test_tdd_order.py::TestTddOrderViolations::test_fires_when_test_and_implementation_share_a_commit` (pytest node id, verified passing when recorded)
- `tests/gates/test_tdd_order.py::TestTddOrderViolations::test_reports_unresolved_rather_than_passing_on_an_unresolvable_pair` (pytest node id, verified passing when recorded)
- `tests/gates/test_tdd_order.py::TestTddOrderViolations::test_ignores_non_tests_edges` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 18 passed (from 18 evidence id(s))
- gates: 60 error(s), 1400 warning(s), 858 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/entity_architecture.md, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3015/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, E501@/home/logan/projects/frob/.claude/worktrees/t-3009/src/frob/narrative/_cli.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3009, REF001@docs/strata/entity_architecture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@tests/unit/strata/entity_arch/storage_cheap.strata, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py
