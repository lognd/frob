## Done report

: T-1137 EPIC frob check --fix: tiered auto-fix engine

Six children rolled up, all done:

- T-1177: Tier-A auto-carry of split-carried waivers. Evidence changed
  post-land (`evidence_changes` on the ticket: T-1763 deleted the whole
  INV006 auto-fix path; the ticket's evidence was re-pointed to the
  DOC007 dotted-form-rewrite handler it still owns).
- T-1260: CLI wiring -- `apply_tier_a_fixes` wired into `frob check --fix`
  plus affected-gate re-verification in the same invocation
  (`src/frob/gates/__init__.py`).
- T-1261: Tier-A batch 2 -- fmt/registry-regen/release-sync/WAIVE004
  handlers (`src/frob/gates/_fix_engine_text.py`,
  `_fix_engine_sync.py`).
- T-1262: Tier-B transaction engine -- apply/verify/rollback per fix,
  sequential not batched (`src/frob/gates/_fix_engine_tier_b.py`).
- T-1263: Tier-C fix-it emission format for agents -- content-required
  findings never edited, never auto-waived, emitted as structured FixIt
  records (`src/frob/gates/_fix_engine_tier_c.py`).
- T-1264: fixability registry field -- `generated_fixability()` maps
  every known rule id to exactly one tier, generated-verified against
  the fix engine's actual handler tables, conflict-detecting
  (`src/frob/gates/_fixability_scan.py`).

Re-verified directly against the code, not just ticket state:
`src/frob/gates/_fix_engine*.py` (base, scope, shared, sync, text,
tier_b, tier_c) and `_fixability_scan.py` all exist and are wired into
`src/frob/gates/__init__.py`. All four acceptance criteria on this epic
map cleanly onto what the six children actually shipped -- no amendment
needed, unlike T-1136's precedent.

## Acceptance

All 4 criteria bound this session (see `frob ticket show T-1137`):

- [0] Tier-A deterministic fixes + affected-gate re-run in one
  invocation: bound to
  `tests/test_gates.py::TestFixEngineTierA::test_doc007_dotted_form_rewrite_applies_and_reverifies_clean`,
  `tests/test_check_runner.py::TestApplyTierAAndReverify::test_doc007_finding_fixed_and_reverified_clean`
- [1] Tier-B transactional apply/verify/rollback: bound to
  `tests/test_gates.py::TestFixEngineTierB::test_clean_fix_commits_and_is_reported_fixed`
- [2] Tier-C never edits/never auto-waives, emits structured fix-it:
  bound to
  `tests/test_gates.py::TestFixEngineTierC::test_todo001_emits_a_fixit_with_no_proposed_patch`
- [3] fixability registry generated-verified, conflict-detecting: bound
  to
  `tests/test_gates.py::TestRuleFixability::test_every_known_rule_id_maps_to_exactly_one_tier`

## Filed

None -- no residue found during re-verification.

## Cuts

None disclosed as outstanding.

### Changed
(no changed files detected -- this ticket only closes an already-shipped
epic; the code changes were made and evidenced by its six children)

### Evidence
- `tests/test_gates.py::TestFixEngineTierA::test_doc007_dotted_form_rewrite_applies_and_reverifies_clean`
- `tests/test_check_runner.py::TestApplyTierAAndReverify::test_doc007_finding_fixed_and_reverified_clean`
- `tests/test_gates.py::TestFixEngineTierB::test_clean_fix_commits_and_is_reported_fixed`
- `tests/test_gates.py::TestFixEngineTierC::test_todo001_emits_a_fixit_with_no_proposed_patch`
- `tests/test_gates.py::TestRuleFixability::test_every_known_rule_id_maps_to_exactly_one_tier`

All 5 re-run fresh this session:
`pytest <the 6 node ids above (0 was 2 ids)> -p no:cacheprovider -q` ->
`SUITE-RESULT: exitstatus=0 collected=6 failed=0`.
