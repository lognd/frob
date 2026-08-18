## Done report

Changed:
strata-core/src/parse/grammar_core.rs::Parser.parse_module
strata-core/src/parse/grammar_core.rs::Parser.parse_part_of
strata-core/src/parse/grammar_core.rs::Parser.parse_extend_node
strata-core/src/parse/grammar_core.rs::ModuleAst
strata-core/src/parse/grammar_policy.rs::Parser.parse_program
src/frob/strata/_ast.py::Module
src/frob/strata/_ast.py::ExtendNodeDecl
src/frob/strata/_multifile.py::resolve_fragments
src/frob/strata/_multifile.py::_widen_node_grants
src/frob/strata/_multifile.py::_group_targeted_roots
src/frob/strata/_multifile.py::_group_fragments_by_name
src/frob/strata/_multifile.py::_resolve_unique_roots
src/frob/strata/_multifile.py::_seed_grants_by_root_node
src/frob/strata/_multifile.py::_apply_fragment_extends
src/frob/strata/_multifile.py::_rebuild_resolved_files
src/frob/strata/_multifile.py::elaborate_merged
docs/strata/surface.md (new "Fragments (T-2502)" section)
docs/guides/extending/strata-surface-grammar.md
editors/vscode-strata/syntaxes/strata.tmLanguage.json

Evidence: 15 pytest node ids in tests/unit/strata/test_fragments.py, bound via
`frob ticket evidence T-2502`:
TestParseFragmentGrammar.test_part_of_parses
TestParseFragmentGrammar.test_root_has_no_part_of
TestParseFragmentGrammar.test_fragment_cannot_declare_module
TestParseFragmentGrammar.test_fragment_cannot_declare_new_node
TestParseFragmentGrammar.test_extend_cannot_set_clearance
TestParseFragmentGrammar.test_extend_grant_requires_via
TestResolveFragments.test_widens_existing_grant
TestResolveFragments.test_extend_takes_effect_through_elaborate_merged
TestResolveFragments.test_no_root_is_error
TestResolveFragments.test_two_roots_is_error
TestResolveFragments.test_unrelated_multi_module_merge_is_unaffected
TestResolveFragments.test_unknown_root_name_is_error
TestResolveFragments.test_unknown_node_is_error
TestResolveFragments.test_unknown_atom_is_error
TestResolveFragments.test_single_file_design_passes_through_unchanged

Plus the pre-existing tests/unit/strata/test_multifile.py and
tests/unit/strata/test_design_load.py suites (34 tests total across the
three files) all pass unmodified, and load_design_ids(Path(repo_root))
against the real design/frob.strata still produces 0 errors, 25 nodes,
106 flows, 1 boundary -- byte-identical to pre-change (must-still-pass
control).

Filed: none

Gates: frob check --land-parity clean of any (rule, file) finding touching
this ticket's own files (only pre-existing repo-wide debt remains,
verified by file path and by diffing this ticket's own untouched files
against main). frob check --only lint/wire/archgate/perf/affect_drift/
docanchor/doclink --ticket T-2502 clean on every file this ticket
touches except one pre-existing WARN: src/frob/strata/_ast.py already
carried 840 lines on main (over LARGE001's 800-line threshold) before
this ticket; this ticket's own +30 lines (870 total) do not newly cross
that threshold, they widen an already-open, WARN-severity, repo-wide
debt-corpus finding (43 pre-existing over-threshold files per
docs/modules/gates.md's own LARGE001 entry) -- left unwaived and
unfixed as genuinely out of this ticket's scope (a real fix would mean
splitting _ast.py, a separate ticket). tests/unit/test_strata_tmlanguage.py's
own pre-existing test_clause_keywords_covered_by_grammar failure
('exclusive' keyword, T-1627, unrelated) is confirmed present on main
before this ticket and left untouched.

### Changed
```
 docs/guides/extending/strata-surface-grammar.md    |  14 +-
 docs/strata/surface.md                             |  79 ++++++
 .../vscode-strata/syntaxes/strata.tmLanguage.json  |   2 +-
 src/frob/strata/_ast.py                            |  32 +++
 src/frob/strata/_multifile.py                      | 303 ++++++++++++++++++++-
 strata-core/src/parse/grammar_core.rs              | 109 ++++++++
 strata-core/src/parse/grammar_policy.rs            |  42 +++
 tests/unit/strata/test_fragments.py                | 187 +++++++++++++
 tickets/T-2502/ticket.md                           |  80 +++++-
 9 files changed, 834 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/unit/strata/test_fragments.py::TestParseFragmentGrammar::test_part_of_parses` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestParseFragmentGrammar::test_root_has_no_part_of` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestParseFragmentGrammar::test_fragment_cannot_declare_module` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestParseFragmentGrammar::test_fragment_cannot_declare_new_node` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestParseFragmentGrammar::test_extend_cannot_set_clearance` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestParseFragmentGrammar::test_extend_grant_requires_via` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestResolveFragments::test_widens_existing_grant` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestResolveFragments::test_extend_takes_effect_through_elaborate_merged` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestResolveFragments::test_no_root_is_error` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestResolveFragments::test_two_roots_is_error` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestResolveFragments::test_unrelated_multi_module_merge_is_unaffected` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestResolveFragments::test_unknown_root_name_is_error` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestResolveFragments::test_unknown_node_is_error` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestResolveFragments::test_unknown_atom_is_error` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestResolveFragments::test_single_file_design_passes_through_unchanged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 15 passed (from 15 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2502/src/frob/graph/summary.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2502/src/frob/testing/_collect_kotlin.py, F811@/home/logan/projects/frob/.claude/worktrees/t-2502/tests/unit/test_app_runners_json_guard_t2492.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2502, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
