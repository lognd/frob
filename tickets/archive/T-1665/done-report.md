## Done report

MEASURED before/after, unscoped:

REF001/002/003 (frob.gates._refs.ref_gate over the full tree), BEFORE
this change (main tip 83e1473a9):
  REF001 (2, WARN, both non-code): tickets/T-1881/evidence/
    stage1-frob-check.json, tickets/T-1959/evidence/class3-reverted.md
  REF002 (2): docs/design/test005-ratchet-schedule.md,
    tickets/T-1881/evidence/fix-measurement.md
  REF003 (0)

AFTER:
  REF001 (2, WARN, both non-code): UNCHANGED, same two files.
  REF001 (0, UNRESOLVED): none in this repo's own tree.
  REF002 (2): UNCHANGED, same two files.
  REF003 (0): UNCHANGED.

Zero net change in live findings, as the T-1985 filer's own measurement
predicted -- but the SUBSTRATE underneath both REF001 findings changed
completely (path/basename text-token matching -> real AST-resolved
Python imports for .py targets), and mid-implementation the rewrite
surfaced and fixed a real bug: initially 3 NEW false REF002s appeared
(src/frob/_cli_parsers/_design.py, _explore.py, _ops.py), traced to
frob.graph.imports._relative_module_name over-walking one package level
for every `__init__.py` importer's own `level=1` relative import
(`_module_name_of` already collapses `__init__.py` to its OWN package's
dotted name; the function then unconditionally dropped ONE MORE
component, so `frob._cli_parsers.__init__`'s `from ._design import ...`
resolved to `frob._design`, which does not exist, instead of the real
`frob._cli_parsers._design`). Fixed in frob/graph/imports.py; the 3
false REF002s disappeared, back to the exact 2 pre-existing REF002s.
Regression test added (tests/test_graph_imports.py::TestBuildImportGraph
::test_relative_import_inside_init_py_resolves_within_its_own_package).

DERIVATION SPLIT of the two remaining live findings (unchanged from
before, both were already non-code and both are correctly REF001 under
either model since import resolution is Python-only and does not apply
to them):
  tickets/T-1881/evidence/stage1-frob-check.json -- a raw `frob check
    --json` capture, zero inbound under both models.
  tickets/T-1959/evidence/class3-reverted.md -- zero inbound under both
    models.

WHAT CHANGED IN THE SUBSTRATE (why the rewrite is not a no-op even
though the live-finding count is unchanged):
- ADDED: `frob.graph.imports.build_import_graph`'s real AST-resolved
  import edges, reversed per-target, as an inbound-reference channel for
  `.py` targets (`_python_resolved_inbound`). This is strictly MORE
  precise than the regex it replaces for every import shape Python's own
  grammar can express (nested `if`/`try`/`TYPE_CHECKING` guards, import
  aliases, star-imports) -- see
  tests/unit/gates/test_refs.py::TestResolvedImportChannel::
  test_import_alias_reaches_the_real_target_not_the_alias_name for a
  shape the OLD regex-token scan could never see at all (an aliased
  import literally never spells the target's own name).
- REMOVED: `_tokens_reach`'s `.py`-only bare-EXTENSIONLESS-STEM matching
  branch (a quoted/backtick token equalling a `.py` file's stem "counted"
  as a reference) -- this was the false-COMFORT class the ticket asked me
  to check for: a dispatch table's bare quoted module-name string or an
  `importlib.import_module(...)` call used to read as a proven reference
  with no verification the string is ever actually evaluated to reach
  that specific file. Full basename-WITH-EXTENSION and full-path text
  mentions are UNCHANGED for ALL target types (Python included) -- T-0396's
  own established rule that a file must be named by its full name to
  count, never merely its bare stem, is untouched; only the .py-specific
  STEM shortcut is gone.
- REMOVED: the regex-based Python `from X import ...`/`import a, b.c`
  text parser (`_FROM_IMPORT_RE`/`_PLAIN_IMPORT_RE`/`_split_import_names`/
  `_python_import_targets`) entirely -- superseded by the real resolver;
  it had no remaining purpose once the stem-matching branch it fed was
  removed.
- ADDED: `Severity.UNRESOLVED` (T-1664) for a `.py` target left at zero
  inbound whose zero-ness might be an artifact of a genuinely
  undecidable dynamic call elsewhere in the repo (`importlib.
  import_module`/`__import__`, or a relative import walking above the
  tracked root) that plausibly names it, by best-effort substring match
  on the target's own dotted module name/stem against the unresolved
  call's raw text (`_unresolved_python_target`). Disclosed as a
  heuristic, not a proof -- see that function's own docstring. Zero live
  findings in this repo's own tree hit this path today (0 UnresolvedImport
  with a `dynamic-import`/`relative-import-above-root` reason currently
  exists anywhere in this repo).

WHAT STAYS ON THE TEXTUAL CHANNEL, AND WHY: markdown links, backtick
MULTI-COMPONENT path mentions (T-0467's doc-link convention), quoted
FULL basename/path literals, `frob:doc`/`frob:describes`/`frob:used-by`/
`frob:tests` directive targets, and non-Python `require`/`include`/`use`
statements -- ALL UNCHANGED, for every target type including `.py`. The
substrate `frob.graph.imports` builds is disclosed Python-only v1
(its own module docstring); every non-Python-import reference shape --
every non-code target (docs, config, data, yaml) and every OTHER
language's source files -- would go completely blind without this
channel, exactly the "non-code targets have no import edges at all"
warning in this ticket's own body. `frob:used-by` (already the anti-lie,
verified-declared channel) is unchanged and remains the correct answer
for a reference genuinely NEITHER channel can see (a runtime-constructed
path, a glob-loaded directory base) -- confirmed by
tests/unit/gates/test_refs.py::TestResolvedImportChannel::
test_constructed_path_from_a_variable_is_not_a_resolved_import, which
still correctly fires REF001 (not UNRESOLVED, not a silent pass) for
exactly that shape.

WAIVER REVIEW (per the ticket's own request): every live `frob:waive
REF001/REF002` in this repo's own docs (4 total, all REF002:
docs/audits/tickets-testing-round2.md, docs/design/tickets-package-
scope-precedent.md, docs/guides/estate-natives-build-rollout.md,
docs/guides/frob-version-policy.md) says a version of "deliberately
singly-anchored, a second consumer would not be genuine" -- NONE say
"reached dynamically" or reference the lexical gap this ticket fixes.
No waiver removed; none were compensating for the false-comfort class.

### Changed
```
 tickets/T-1665/done-report.md | 125 ++++++++++++++++++++++++
 tickets/T-1665/ticket.md      | 219 +++++++++++++++++++++++++++++++++++++++++-
 2 files changed, 341 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_refs_gate.py::TestTiers::test_zero_refs_warns_ref001` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestTiers::test_one_ref_weak_warns_ref002` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestTiers::test_two_refs_passes` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestUsedByDeclaration::test_valid_declaration_counts_not_dangling` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestUsedByDeclaration::test_dangling_declaration_nonexistent_consumer_fails` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestUsedByDeclaration::test_dangling_declaration_non_reaching_consumer_fails` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestEntrypointAllowlist::test_allowlisted_file_is_exempt` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestEntrypointAllowlist::test_non_allowlisted_orphan_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestNativeStubLinking::test_linked_pyi_beside_matching_manifest_does_not_fire_ref001` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestNativeStubLinking::test_unlinked_pyi_with_no_adjacent_module_still_fires_ref001` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestNativeStubLinking::test_pyi_with_manifest_present_but_module_name_mismatch_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestSeverityAndDegrade::test_all_violations_are_warn_severity` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestSeverityAndDegrade::test_no_tracked_files_returns_empty` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestReferenceDetection::test_bare_prose_mention_does_not_count_as_a_reference` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestReferenceDetection::test_markdown_link_counts_as_a_reference` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestReviewerRegressionRound2::test_multi_name_from_import_target_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestReviewerRegressionRound2::test_parenthesized_from_import_target_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestReviewerRegressionRound2::test_dispatch_table_bare_string_target_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestReviewerRegressionRound2::test_pytest_collected_test_file_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestReviewerRegressionRound2::test_dead_non_test_file_under_tests_dir_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestReviewerRegressionRound2::test_registry_style_yaml_with_only_prose_mentions_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestReviewerRegressionRound2::test_genuinely_unreferenced_module_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestMarkdownWaive::test_ref002_on_md_doc_suppressed_by_inline_waive` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestMarkdownWaive::test_ref002_on_md_doc_without_waive_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestBacktickTokenizer::test_backtick_wrapped_path_mention_counts_as_reference` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestBacktickTokenizer::test_backtick_wrapped_bare_identifier_not_treated_as_reference` (pytest node id, verified passing when recorded)
- `tests/test_graph_imports.py::TestBuildImportGraph::test_resolves_a_real_intra_repo_import_edge` (pytest node id, verified passing when recorded)
- `tests/test_graph_imports.py::TestBuildImportGraph::test_dynamic_import_reports_unresolved_not_dropped` (pytest node id, verified passing when recorded)
- `tests/test_graph_imports.py::TestBuildImportGraph::test_non_python_file_reports_unsupported_language_unresolved` (pytest node id, verified passing when recorded)
- `tests/test_graph_imports.py::TestBuildImportGraph::test_stdlib_import_counts_as_external_not_unresolved` (pytest node id, verified passing when recorded)
- `tests/test_graph_imports.py::TestBuildImportGraph::test_relative_import_resolves_within_package` (pytest node id, verified passing when recorded)
- `tests/test_graph_imports.py::TestBuildImportGraph::test_star_import_resolves_the_module_not_its_names` (pytest node id, verified passing when recorded)
- `tests/test_graph_imports.py::TestBuildImportGraph::test_relative_import_inside_init_py_resolves_within_its_own_package` (pytest node id, verified passing when recorded)
- `tests/test_graph_imports.py::TestBuildImportGraph::test_unreadable_file_is_reported_unresolved_not_silently_skipped` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_refs.py::TestResolvedImportChannel::test_import_alias_reaches_the_real_target_not_the_alias_name` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_refs.py::TestResolvedImportChannel::test_constructed_path_from_a_variable_is_not_a_resolved_import` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_refs.py::TestUnresolvedSeverity::test_dynamic_import_call_naming_the_target_reports_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_refs.py::TestUnresolvedSeverity::test_unrelated_dynamic_import_does_not_launder_a_real_orphan` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_refs.py::TestUnresolvedSeverity::test_resolved_import_wins_over_unresolved_when_both_exist` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 39 passed (from 39 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: DSL001@CHANGELOG.md, F401@/home/logan/projects/frob/.claude/worktrees/t1665-only/tests/unit/test_tickets_evidence_only_scope.py
