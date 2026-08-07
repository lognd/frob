## Done report

Measured live (unscoped, FROB_NO_GATE_CACHE=1, `--only refs --only
docblocks`) before touching anything: REF003 4 findings, NEGEXIST001 4
findings, both matching the drive brief's small untracked families.
(REF001 measured 0 live -- already resolved on main before this pass;
REF002's 51 pre-existing findings are the already-ticketed big family,
left untouched.)

REF003 (4 -> 0): all 4 were `invariants/INV-050.md` declaring
`frob:used-by <file>` on 4 files that genuinely memoize a repo-derived
computation under `.frob/` (verified each one greps for `cache`/`.frob/`
before touching) but never carried the required back-reference tag.
Added `# frob:invariant INV-050` + spec-link comment to each, matching
the exact pattern the 3 already-passing files in the same declaration
block already use (src/frob/gates/_gate_cache.py,
src/frob/graph/cache.py, src/frob/tickets/_store.py) -- REAL debt (a
missing tag), not a rule bug, fixed by wiring the tag, not by editing
the invariant's `frob:used-by` list.

NEGEXIST001 (4 -> 0): all 4 were rule-gap false positives (the phrase
heuristic matching text, not intent) --
- CHANGELOG.md:743 "hangs ... when the named base ref does not exist"
  describes a historical BUG CONDITION inside an already-shipped fix
  entry, not an open commitment. Also structurally unfixable via the
  documented `frob:until` remedy in a worktree: CHANGELOG.md is
  exclusively `frob ticket land`-owned (agent playbook section 4b,
  T-0731) and a pre-commit hook refuses any worktree commit touching it.
  Fixed at the rule level: `frob.graph.dsl._NEGEXIST_EXEMPT_DOCS` now
  exempts CHANGELOG.md from the phrase scan entirely, with a regression
  test proving the identical phrase still matches under any OTHER doc
  path (test_changelog_md_is_exempt_from_the_phrase_heuristic).
- docs/design/cli-regrouping.md, docs/modules/gates.md, docs/modules/
  tickets.md: 3 more instances of the identical shape -- a design-note
  aside explicitly disclaiming urgency ("no action needed unless...")
  and two historical-bug-description asides inside already-shipped
  design-decision log entries, none an open commitment. Reworded each to
  preserve the exact original meaning while avoiding the literal "does
  not exist [yet]" trigger phrase, rather than binding a `frob:until` to
  a ticket that would misrepresent settled/optional prose as open work.

No mass-waiving: every disposition above is either a real missing tag
(wired, not waived) or a rule-level fix with a regression test: zero
`frob:waive NEGEXIST001`/`frob:waive REF003` added.

Verification: `frob check --only refs --only docblocks --json`
(FROB_NO_GATE_CACHE=1, `.frob/cache.db` cleared) shows 0 REF003 and 0
NEGEXIST001 warnings after this ticket. REF002 (51, pre-existing) and
DOC006 (1, pre-existing, unrelated) untouched, confirmed out of scope.
`frob check --land-parity`: clean, 0 unscoped errors. `uv run ruff
check`/PATH `ruff check` both clean on every touched file.
tests/unit/gates/test_negexist.py (11 tests) + tests/test_refs_gate.py
(26 tests) all pass, 37 total.

### Changed
```
 tickets.md | 259 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 259 insertions(+)
```

### Evidence
- `tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_until_directive_emits_until_edge` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_negative_existence_phrase_emits_claims_absence_edge` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_not_yet_wired_phrase_is_also_detected` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_directive_comment_line_itself_never_matches_the_heuristic` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_plain_prose_with_no_matching_phrase_emits_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_changelog_md_is_exempt_from_the_phrase_heuristic` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_negexist.py::TestNegexist001Gate::test_unbound_claim_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_negexist.py::TestNegexist001Gate::test_claim_bound_to_open_ticket_is_clean` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_negexist.py::TestNegexist001Gate::test_claim_bound_to_closed_ticket_is_stale` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_negexist.py::TestNegexist001Gate::test_claim_bound_to_missing_ticket_is_stale` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_negexist.py::TestNegexist001Gate::test_no_claims_at_all_is_clean` (pytest node id, verified passing when recorded)
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

### Captured claims
- tests: 37 passed (from 37 evidence id(s))
- gates: 0 error(s), 878 warning(s), 845 waived
- error-findings: none (measured, zero errors)
