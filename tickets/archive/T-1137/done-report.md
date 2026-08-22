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

### Changed
```
 tickets/T-1135/ticket.md      |  4 +-
 tickets/T-1137/ticket.md      | 26 ++++++++++---
 tickets/T-1219/done-report.md | 88 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-1219/ticket.md      | 23 ++++++++++-
 tickets/T-2468/ticket.md      |  2 +-
 5 files changed, 135 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierA::test_doc007_dotted_form_rewrite_applies_and_reverifies_clean` (pytest node id, verified passing when recorded)
- `tests/test_check_runner.py::TestApplyTierAAndReverify::test_doc007_finding_fixed_and_reverified_clean` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierB::test_clean_fix_commits_and_is_reported_fixed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierC::test_todo001_emits_a_fixit_with_no_proposed_patch` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRuleFixability::test_every_known_rule_id_maps_to_exactly_one_tier` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOCENUM001@docs/modules/gates.md, DRIFT002@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1135/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1135/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1135/src/frob/gates/_dup_graph_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1135/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-1135/src/frob/vet/_capability.py, GATERULE001@src/frob/gates/_gates_schema.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md, missing-argument@tests/unit/test_ticket_runner_land_release.py


frob:no-behavior-change reason="epic-rollup close: T-1137's 6 children (T-1177,T-1260..T-1264) already shipped and archived done; all 4 acceptance criteria bind cleanly to existing evidence, no code change needed here"
