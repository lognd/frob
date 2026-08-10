---
id: T-1665
title: 'REF001: decide inbound references from resolved imports and calls, not path/basename
  text mentions'
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: high
blocked_by:
- T-1663
- T-1985
parent: T-1662
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_refs.py
- docs/modules/gates.md
- tests/unit/gates/test_refs.py
- tests/test_refs_gate.py
- tests/test_graph_imports.py
- src/frob/graph/imports.py
- design/frob.strata
- docs/modules/graph.md
- docs/commands/check.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'narrow the tests/** umbrella to the one test file REF001''s change needs.
    This was the last outstanding TICK009 breadth nudge and it collapses the wave
    partition: with it present, frob ticket wave --agents 4 folds nearly every ticket
    into one group. T-1985 (the resolved-import substrate this ticket depends on)
    has landed, so T-1665 is now startable and the umbrella would lease the entire
    test tree.'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/gates/test_refs.py
  reason: 'narrow the tests/** umbrella to the one test file REF001''s change needs.
    This was the last outstanding TICK009 breadth nudge and it collapses the wave
    partition: with it present, frob ticket wave --agents 4 folds nearly every ticket
    into one group. T-1985 (the resolved-import substrate this ticket depends on)
    has landed, so T-1665 is now startable and the umbrella would lease the entire
    test tree.'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_refs_gate.py
  reason: 'Widened to include the existing test file (tests/test_refs_gate.py) since

    the semantic rewrite changes one existing test''s expected outcome

    (dispatch-table dynamic import: was a silent pass, now honestly

    UNRESOLVED). Also widened to tests/test_graph_imports.py: while wiring

    the resolved-import substrate into ref_gate, found and fixed a real bug

    in frob.graph.imports._relative_module_name (an __init__.py importer''s

    level=1 relative import over-walked one package level, since

    _module_name_of already collapses __init__.py to its own package name)

    -- needs a regression test alongside the existing import-graph suite.

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_graph_imports.py
  reason: 'Widened to include the existing test file (tests/test_refs_gate.py) since

    the semantic rewrite changes one existing test''s expected outcome

    (dispatch-table dynamic import: was a silent pass, now honestly

    UNRESOLVED). Also widened to tests/test_graph_imports.py: while wiring

    the resolved-import substrate into ref_gate, found and fixed a real bug

    in frob.graph.imports._relative_module_name (an __init__.py importer''s

    level=1 relative import over-walked one package level, since

    _module_name_of already collapses __init__.py to its own package name)

    -- needs a regression test alongside the existing import-graph suite.

    '
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/graph/**
  reason: 'Narrowing the broad src/frob/graph/** glob to the one file actually

    touched (imports.py, the __init__.py relative-import bug fix) -- the

    wildcard pulled in the whole graph package''s unrelated frob:doc closure

    obligations (docs/modules/graph.md#public-api etc. across dozens of

    unrelated symbols), producing a wall of SCOPE002 findings for doc

    anchors this ticket never touches. Also adding design/frob.strata (new

    capability-declaration entries for the new test file''s exec/fs.write

    observations) and docs/modules/graph.md/docs/commands/check.md (closure

    targets of files genuinely in scope).

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/graph/imports.py
  reason: 'Narrowing the broad src/frob/graph/** glob to the one file actually

    touched (imports.py, the __init__.py relative-import bug fix) -- the

    wildcard pulled in the whole graph package''s unrelated frob:doc closure

    obligations (docs/modules/graph.md#public-api etc. across dozens of

    unrelated symbols), producing a wall of SCOPE002 findings for doc

    anchors this ticket never touches. Also adding design/frob.strata (new

    capability-declaration entries for the new test file''s exec/fs.write

    observations) and docs/modules/graph.md/docs/commands/check.md (closure

    targets of files genuinely in scope).

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: design/frob.strata
  reason: 'Narrowing the broad src/frob/graph/** glob to the one file actually

    touched (imports.py, the __init__.py relative-import bug fix) -- the

    wildcard pulled in the whole graph package''s unrelated frob:doc closure

    obligations (docs/modules/graph.md#public-api etc. across dozens of

    unrelated symbols), producing a wall of SCOPE002 findings for doc

    anchors this ticket never touches. Also adding design/frob.strata (new

    capability-declaration entries for the new test file''s exec/fs.write

    observations) and docs/modules/graph.md/docs/commands/check.md (closure

    targets of files genuinely in scope).

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/modules/graph.md
  reason: 'Narrowing the broad src/frob/graph/** glob to the one file actually

    touched (imports.py, the __init__.py relative-import bug fix) -- the

    wildcard pulled in the whole graph package''s unrelated frob:doc closure

    obligations (docs/modules/graph.md#public-api etc. across dozens of

    unrelated symbols), producing a wall of SCOPE002 findings for doc

    anchors this ticket never touches. Also adding design/frob.strata (new

    capability-declaration entries for the new test file''s exec/fs.write

    observations) and docs/modules/graph.md/docs/commands/check.md (closure

    targets of files genuinely in scope).

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/commands/check.md
  reason: 'Narrowing the broad src/frob/graph/** glob to the one file actually

    touched (imports.py, the __init__.py relative-import bug fix) -- the

    wildcard pulled in the whole graph package''s unrelated frob:doc closure

    obligations (docs/modules/graph.md#public-api etc. across dozens of

    unrelated symbols), producing a wall of SCOPE002 findings for doc

    anchors this ticket never touches. Also adding design/frob.strata (new

    capability-declaration entries for the new test file''s exec/fs.write

    observations) and docs/modules/graph.md/docs/commands/check.md (closure

    targets of files genuinely in scope).

    '
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_refs_gate.py::TestTiers::test_zero_refs_warns_ref001
- tests/test_refs_gate.py::TestTiers::test_one_ref_weak_warns_ref002
- tests/test_refs_gate.py::TestTiers::test_two_refs_passes
- tests/test_refs_gate.py::TestUsedByDeclaration::test_valid_declaration_counts_not_dangling
- tests/test_refs_gate.py::TestUsedByDeclaration::test_dangling_declaration_nonexistent_consumer_fails
- tests/test_refs_gate.py::TestUsedByDeclaration::test_dangling_declaration_non_reaching_consumer_fails
- tests/test_refs_gate.py::TestEntrypointAllowlist::test_allowlisted_file_is_exempt
- tests/test_refs_gate.py::TestEntrypointAllowlist::test_non_allowlisted_orphan_still_fires
- tests/test_refs_gate.py::TestNativeStubLinking::test_linked_pyi_beside_matching_manifest_does_not_fire_ref001
- tests/test_refs_gate.py::TestNativeStubLinking::test_unlinked_pyi_with_no_adjacent_module_still_fires_ref001
- tests/test_refs_gate.py::TestNativeStubLinking::test_pyi_with_manifest_present_but_module_name_mismatch_still_fires
- tests/test_refs_gate.py::TestSeverityAndDegrade::test_all_violations_are_warn_severity
- tests/test_refs_gate.py::TestSeverityAndDegrade::test_no_tracked_files_returns_empty
- tests/test_refs_gate.py::TestReferenceDetection::test_bare_prose_mention_does_not_count_as_a_reference
- tests/test_refs_gate.py::TestReferenceDetection::test_markdown_link_counts_as_a_reference
- tests/test_refs_gate.py::TestReviewerRegressionRound2::test_multi_name_from_import_target_not_flagged
- tests/test_refs_gate.py::TestReviewerRegressionRound2::test_parenthesized_from_import_target_not_flagged
- tests/test_refs_gate.py::TestReviewerRegressionRound2::test_dispatch_table_bare_string_target_not_flagged
- tests/test_refs_gate.py::TestReviewerRegressionRound2::test_pytest_collected_test_file_not_flagged
- tests/test_refs_gate.py::TestReviewerRegressionRound2::test_dead_non_test_file_under_tests_dir_still_fires
- tests/test_refs_gate.py::TestReviewerRegressionRound2::test_registry_style_yaml_with_only_prose_mentions_still_fires
- tests/test_refs_gate.py::TestReviewerRegressionRound2::test_genuinely_unreferenced_module_still_fires
- tests/test_refs_gate.py::TestMarkdownWaive::test_ref002_on_md_doc_suppressed_by_inline_waive
- tests/test_refs_gate.py::TestMarkdownWaive::test_ref002_on_md_doc_without_waive_still_fires
- tests/test_refs_gate.py::TestBacktickTokenizer::test_backtick_wrapped_path_mention_counts_as_reference
- tests/test_refs_gate.py::TestBacktickTokenizer::test_backtick_wrapped_bare_identifier_not_treated_as_reference
- tests/test_graph_imports.py::TestBuildImportGraph::test_resolves_a_real_intra_repo_import_edge
- tests/test_graph_imports.py::TestBuildImportGraph::test_dynamic_import_reports_unresolved_not_dropped
- tests/test_graph_imports.py::TestBuildImportGraph::test_non_python_file_reports_unsupported_language_unresolved
- tests/test_graph_imports.py::TestBuildImportGraph::test_stdlib_import_counts_as_external_not_unresolved
- tests/test_graph_imports.py::TestBuildImportGraph::test_relative_import_resolves_within_package
- tests/test_graph_imports.py::TestBuildImportGraph::test_star_import_resolves_the_module_not_its_names
- tests/test_graph_imports.py::TestBuildImportGraph::test_relative_import_inside_init_py_resolves_within_its_own_package
- tests/test_graph_imports.py::TestBuildImportGraph::test_unreadable_file_is_reported_unresolved_not_silently_skipped
- tests/unit/gates/test_refs.py::TestResolvedImportChannel::test_import_alias_reaches_the_real_target_not_the_alias_name
- tests/unit/gates/test_refs.py::TestResolvedImportChannel::test_constructed_path_from_a_variable_is_not_a_resolved_import
- tests/unit/gates/test_refs.py::TestUnresolvedSeverity::test_dynamic_import_call_naming_the_target_reports_unresolved
- tests/unit/gates/test_refs.py::TestUnresolvedSeverity::test_unrelated_dynamic_import_does_not_launder_a_real_orphan
- tests/unit/gates/test_refs.py::TestUnresolvedSeverity::test_resolved_import_wins_over_unresolved_when_both_exist
designated_repro_test: tests/test_refs_gate.py::TestReviewerRegressionRound2::test_dispatch_table_bare_string_target_not_flagged
evidence_changes:
- old_node: tests/test_refs_gate.py::TestReviewerRegressionRound2::test_dispatch_table_bare_string_target_reports_unresolved_not_dead
  new_node: tests/test_refs_gate.py::TestReviewerRegressionRound2::test_dispatch_table_bare_string_target_not_flagged
  reason: kept the original node id/name so T-0396/T-0831/T-1653's own archived evidence
    bindings stay valid; only the assertion changed
  actor: logan
  at: '2026-08-10'
threat: null
component: null
anchor: false
anchor_reason: null
---
REF001 decides whether a file has any inbound reference by searching other files' TEXT for its full repo-relative path or its BARE BASENAME. Its own module docstring says so: "by file Y if Y names X (full repo-relative path or bare basename) in a ... literal, a backtick-wrapped MULTI-COMPONENT path mention".

That is wrong in both directions:
- FALSE POSITIVE (reports dead when live): a module reached through an import alias, a constructed path (`root / "sub" / name`), a dynamic import, a registry/dispatch table, or a plugin entry point is never NAMED anywhere, so it reads as unreferenced.
- FALSE NEGATIVE (reports live when dead): a file merely mentioned in prose, a changelog entry, or a comment counts as referenced. A genuinely dead module stays hidden as long as some document names it.

Both matter. The false positives generate waivers that then have to be maintained forever (REF002 is at 51 findings largely for this reason), and the false negatives defeat the rule's entire purpose.

Raise it to semantics:
- For code targets, an inbound reference means a resolved IMPORT or a resolved call/attribute reference reaching that module -- frob.graph.callgraph and the snapshot's edges already model this.
- Keep an explicit, NARROW textual channel for the genuinely non-code cases the rule must still cover: a config file named in a template, a data file read by path. Those should be an explicit declared-reference form (`frob:used-by`, which already exists) rather than an accidental substring hit.
- Per T-1664, a target whose reachability cannot be resolved must report UNRESOLVED, not "referenced" and not "dead".

Expect the finding set to CHANGE substantially in both directions, not merely shrink. Report before/after with a classification of everything that appears and disappears -- a file that stops being flagged because it is genuinely imported is a fix; one that starts being flagged because only prose named it is the rule finally working.

While here, check whether the existing REF001 waivers were compensating for the lexical gap. If most of them say some version of "reached dynamically", that is direct evidence for the semantic model and those waivers should be REMOVED, not migrated.

## Failure log
- 2026-08-10 attempt 1: investigated, not landed: no resolved-import substrate exists in frob.graph (EdgeKind is directive-edges-only; callgraph.py excludes public/exported symbols by design); measured today's REF001 findings (2, both non-code, 0 waived) -- semantic rewrite would not change either. Design + prerequisite filed as T-1985, blocking this ticket.