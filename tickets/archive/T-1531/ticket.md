---
id: T-1531
title: auto-repair the recurring land-refusal classes via Tier-A/B fix handlers (strata
  declarations, ticket edges, report refresh, draft renumber)
state: done
kind: feature
origin: human
created: '2026-08-04'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine.py
- src/frob/strata/_sync_may.py
- tests/unit/strata/test_sync_may.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: 'T-1531 auto-repair land-refusal classes: SYS104/SYS100 Tier-A handlers
    + writer + tests'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/strata/_sync_may.py
  reason: 'T-1531 auto-repair land-refusal classes: SYS104/SYS100 Tier-A handlers
    + writer + tests'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/unit/strata/test_sync_may.py
  reason: 'T-1531 auto-repair land-refusal classes: SYS104/SYS100 Tier-A handlers
    + writer + tests'
  actor: logan
  at: '2026-08-05'
evidence:
- tests/unit/strata/test_sync_may.py::TestSyncMayReport::test_no_drift_reports_clean
- tests/unit/strata/test_sync_may.py::TestSyncMayReport::test_widens_existing_via_list
- tests/unit/strata/test_sync_may.py::TestSyncMayReport::test_inserts_new_grant_when_none_declared
- tests/unit/strata/test_sync_may.py::TestSyncMayReport::test_no_design_files_reports_empty
- tests/unit/strata/test_sync_may.py::TestSyncMayReport::test_bad_design_file_propagates_load_error
- tests/unit/strata/test_sync_may.py::TestSyncMayReport::test_ambiguous_code_binding_propagates_as_error
- tests/unit/strata/test_sync_may.py::TestApplySyncMay::test_writes_only_changed_files
- tests/test_gates.py::TestFixEngineTierA::test_sys104_interface_union_applies_via_apply_tier_a_fixes
- tests/test_gates.py::TestFixEngineTierA::test_sys104_no_design_dir_is_a_no_op
- tests/test_gates.py::TestFixEngineTierA::test_sys100_may_via_union_applies_via_apply_tier_a_fixes
- tests/test_gates.py::TestFixEngineTierA::test_sys100_no_design_dir_is_a_no_op
designated_repro_test: null
threat: null
component: null
---
Every land refusal on 2026-08-04 was one of a small set of classes, each hand-fixed with the SAME deterministic recipe dozens of times. Extend the tiered fix engine (Tier-A deterministic; Tier-B T-1262 apply-verify-rollback) with handlers so land repairs them automatically before refusing: (1) SYS100 undeclared capability -> add the observed file to the named node's may-via list (sorted union; compact grammar); (2) SYS104 undeclared public symbol -> add to the node's compact attr interface=[...] list (sorted union); (3) COV002 changed-symbol-without-edge -> insert '# frob:ticket <landing-id>' above the symbol when the diff belongs to the landing ticket; (4) ClaimDivergence -> re-run done-report with the existing why text (the recap re-measures; this is exactly the documented manual recipe); (5) TICK006 phantom draft citation -> refile + renumber-to-cited-id when the citation names a draft absent from ledger+archive; (6) E501 introduced by merge -> ruff-format the specific lines (Tier-A fmt already close). Every applied fix goes through Tier-B verify-or-rollback and is loudly logged; anything not exactly matching a recipe still refuses. Success metric: a re-land of a branch whose only findings are in these classes succeeds with zero human edits. Builds on T-1481 (check --fix CLI) and complements T-1514's free pre-commit refusals.