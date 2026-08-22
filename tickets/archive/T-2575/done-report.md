## Done report

Changed:
src/frob/lang/__init__.py::_parse
src/frob/lang/__init__.py::_warn_unsupported_extension
src/frob/lang/__init__.py::_parse_uncached_and_store
src/frob/lang/__init__.py::parse_file
src/frob/lang/__init__.py::extract_imports
src/frob/lang/__init__.py::iter_identifiers
src/frob/lang/__init__.py::raw_tree
src/frob/lang/__init__.py::_parse_file_with_artifact_cache
src/frob/lang/__init__.py::_parse_and_populate_artifact_cache
src/frob/lang/__init__.py::_parse_file_uncached
src/frob/lang/__init__.py::reset_parse_cache
src/frob/arch/__init__.py::_analyze_one_file (removed _has_tree_sitter_grammar)
src/frob/gates/__init__.py::_perf_gate_parse_files
src/frob/gates/_coverage_sites.py::_perf_examined_sites
src/frob/tickets/_land.py::_raw_tree_for_worktree_file
src/frob/tickets/_land.py::_raw_tree_for_temp_source
src/frob/tickets/_land.py::_genuine_comment_lines
src/frob/xref/__init__.py::_parsed_definition
src/frob/outline/__init__.py::_parse_for_outline
docs/modules/lang.md, docs/modules/graph.md (signature snippets updated)

Evidence:
tests/test_lang.py::TestErrors::test_unsupported_extension_warns_by_default
tests/test_lang.py::TestErrors::test_unsupported_extension_declared_heterogeneous_no_warning
tests/test_lang.py::TestErrors::test_unsupported_extension_non_declaring_still_warns
tests/test_lang.py::TestErrors::test_unsupported_extension_warning_deduplicates_per_run (designated repro, FAILED_AT_PARENT confirmed against commit 4fd66b1c0 via --check-repro)
tests/test_lang.py::TestErrors::test_unsupported_extension_warning_resets_per_run

Measured caller split (git grep, code only): 49 files call parse_file/extract_imports/
iter_identifiers/raw_tree/symbol_tree; 6 files referenced tree_sitter_extensions
(arch/__init__.py, gates/__init__.py, gates/_coverage_sites.py, lang/__init__.py itself,
tickets/_land.py, xref/__init__.py) -- confirms the ticket's 6-vs-25+ claim (actual: 6-vs-49).
outline/__init__.py's separate .strata carve-out (T-0129) folded onto the same
expect_heterogeneous declaration.

Filed: none (no out-of-scope work found requiring a new ticket)

Gates: frob check --land-parity clean with respect to this ticket's scope -- 46
unscoped errors remain, none touching a T-2575-scoped file/symbol (all pre-existing,
confirmed by diffing the finding list against the ticket's declared scope both before
and after this ticket's fixes, which reduced the count from 50 to 46 by resolving 4
COV002 findings on T-2575's own touched symbols). frob test --base main: PASS, 28
python test(s) recorded stable. gate:SCOPE: 0 errors (was 2: frob.lock and
tests/test_lang.py added to scope). DRIFT001 on parse_file acked
(digest c7ca45f4/c60cb622) with reason recorded via frob ack.

### Changed
```
 docs/modules/graph.md             |   4 +-
 docs/modules/lang.md              |  16 +++-
 src/frob/arch/__init__.py         |  52 +++++-----
 src/frob/gates/__init__.py        |  14 ++-
 src/frob/gates/_coverage_sites.py |   3 +-
 src/frob/lang/__init__.py         | 194 +++++++++++++++++++++++++++++++++-----
 src/frob/outline/__init__.py      |  20 ++--
 src/frob/tickets/_land.py         |  41 ++++----
 src/frob/xref/__init__.py         |  11 ++-
 tests/test_lang.py                | 109 +++++++++++++++++++++
 tickets/T-2575/ticket.md          |  54 ++++++++++-
 11 files changed, 433 insertions(+), 85 deletions(-)
```

### Evidence
- `tests/test_lang.py::TestErrors::test_unsupported_extension_warns_by_default` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestErrors::test_unsupported_extension_declared_heterogeneous_no_warning` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestErrors::test_unsupported_extension_non_declaring_still_warns` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestErrors::test_unsupported_extension_warning_deduplicates_per_run` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestErrors::test_unsupported_extension_warning_resets_per_run` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2561/ticket.md, DOC006@tickets/T-2570/ticket.md, DOC006@tickets/T-2585/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2575/src/frob/app/ticket_runner/_ledger_mirror.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2575/src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2575/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2575, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
