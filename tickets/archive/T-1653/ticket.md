---
id: T-1653
title: Fix REF003 missing invariant back-refs + NEGEXIST001 false positives on historical/design
  prose
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- invariants/INV-050.md
- src/frob/testing/_collect_shared.py
- src/frob/gates/_coverage.py
- src/frob/perf/_sketch_store.py
- src/frob/app/_check_chunking.py
- src/frob/graph/dsl.py
- docs/design/cli-regrouping.md
- docs/modules/gates.md
- docs/modules/tickets.md
- tests/unit/gates/test_negexist.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/gates/test_negexist.py
  reason: added a regression test for the CHANGELOG.md negexist exemption this ticket
    introduces
  actor: logan
  at: '2026-08-06'
evidence:
- tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_until_directive_emits_until_edge
- tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_negative_existence_phrase_emits_claims_absence_edge
- tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_not_yet_wired_phrase_is_also_detected
- tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_directive_comment_line_itself_never_matches_the_heuristic
- tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_plain_prose_with_no_matching_phrase_emits_nothing
- tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_changelog_md_is_exempt_from_the_phrase_heuristic
- tests/unit/gates/test_negexist.py::TestNegexist001Gate::test_unbound_claim_is_flagged
- tests/unit/gates/test_negexist.py::TestNegexist001Gate::test_claim_bound_to_open_ticket_is_clean
- tests/unit/gates/test_negexist.py::TestNegexist001Gate::test_claim_bound_to_closed_ticket_is_stale
- tests/unit/gates/test_negexist.py::TestNegexist001Gate::test_claim_bound_to_missing_ticket_is_stale
- tests/unit/gates/test_negexist.py::TestNegexist001Gate::test_no_claims_at_all_is_clean
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
designated_repro_test: null
threat: null
component: null
---
Fixes four small, previously-untracked doc-drift gate families measured
on this repo's own tree (small enough to finish in one pass):

REF003 (4 -> 0): invariants/INV-050.md declared `frob:used-by` on 4 files
that genuinely memoize repo-derived computations under `.frob/` but never
carried the required back-reference tag -- added `# frob:invariant
INV-050` + spec link to each (src/frob/testing/_collect_shared.py,
src/frob/gates/_coverage.py, src/frob/perf/_sketch_store.py,
src/frob/app/_check_chunking.py), matching the pattern the 3 already-
passing files in the same declaration already use.

NEGEXIST001 (4 -> 0): all 4 were the same rule-gap shape (detector
matching prose text, not intent) --
- CHANGELOG.md:743's "does not exist" describes a historical bug
  condition inside an already-shipped fix entry, not an open commitment;
  worse, CHANGELOG.md is exclusively `frob ticket land`-owned (agent
  playbook section 4b) so no worktree agent could ever apply the
  documented `frob:until` remedy there even if it were the right fix.
  Fixed at the rule level: `frob.graph.dsl._NEGEXIST_EXEMPT_DOCS` now
  exempts CHANGELOG.md from the negexist-phrase scan entirely.
- docs/design/cli-regrouping.md, docs/modules/gates.md, docs/modules/
  tickets.md: 3 more instances of the same shape (a design-note aside
  and two historical-bug-description asides in already-shipped design-
  decision entries, none an open commitment) -- reworded each to avoid
  the literal "does not exist [yet]" trigger phrase while preserving the
  exact original meaning, rather than binding a `frob:until` to a ticket
  that would misrepresent these as open work.

Measured before/after (unscoped, FROB_NO_GATE_CACHE=1, `--only refs
--only docblocks`): REF003 4->0, NEGEXIST001 4->0. REF002 (pre-existing,
51 findings) and DOC006 (1 pre-existing, unrelated finding) are untouched
-- out of this ticket's scope, already-known debt piles per the drive
brief.