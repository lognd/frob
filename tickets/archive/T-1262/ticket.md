---
id: T-1262
title: 'gates --fix Tier-B transaction engine: apply-verify-rollback per fix'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1137
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine_tier_b.py
- tests/test_gates.py
- docs/design/check-fix-engine.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/design/check-fix-engine.md
  reason: Tier-B engine's frob:doc anchor lives there; must update the doc in the
    same diff (AFFECT001)
  actor: logan
  at: '2026-08-03'
- op: add
  glob: design/frob.strata
  reason: capability effects/interface declarations for the new module must live in
    the same node
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_gates.py::TestFixEngineTierB::test_clean_fix_commits_and_is_reported_fixed
- tests/test_gates.py::TestFixEngineTierB::test_regressing_fix_is_rolled_back_byte_for_byte
- tests/test_gates.py::TestFixEngineTierB::test_new_error_violation_after_fix_rolls_back
- tests/test_gates.py::TestFixEngineTierB::test_multiple_fixes_verified_sequentially_not_batched
- tests/test_gates.py::TestFixEngineTierB::test_no_marker_files_is_a_no_op
designated_repro_test: null
acceptance:
- text: GIVEN a Tier-B fix that applies cleanly WHEN its affected_gates and bound_tests
    all re-verify clean THEN the fix is committed and reported as fixed
  evidence:
  - tests/test_gates.py::TestFixEngineTierB::test_clean_fix_commits_and_is_reported_fixed
- text: GIVEN a Tier-B fix that introduces a regression WHEN affected_gates or bound_tests
    fail after applying THEN every touched file is restored byte-for-byte from its
    pre-fix backup and a FixRolledBack record discloses which gate/test regressed
  evidence:
  - tests/test_gates.py::TestFixEngineTierB::test_regressing_fix_is_rolled_back_byte_for_byte
  - tests/test_gates.py::TestFixEngineTierB::test_new_error_violation_after_fix_rolls_back
- text: GIVEN N Tier-B fixes in one --fix invocation THEN each is applied and verified
    sequentially, never batched, so a rollback never has to bisect more than one fix
  evidence:
  - tests/test_gates.py::TestFixEngineTierB::test_multiple_fixes_verified_sequentially_not_batched
threat: null
component: null
---
Build the Tier-B transactional fix engine per docs/design/check-fix-engine.md
"Transaction / rollback model" section: new src/frob/gates/_fix_engine_tier_b.py
with TIER_B_HANDLERS: dict[str, TierBHandler], a TierBFix model (backup
bytes, affected_gates, bound_tests), and the apply-verify-commit-or-
rollback engine itself (snapshot pre-fix bytes, apply, re-run affected
gates + bound tests, restore from backup byte-for-byte on any regression,
emit a disclosed FixRolledBack record naming what regressed). Ship
sequential, per-fix verification -- never batched -- exactly as the design
doc specifies. No concrete Tier-B handler is required to exist yet as
part of THIS ticket's scope beyond one minimal reference handler proving
the rollback path end-to-end (a synthetic/test-fixture rule is
acceptable, or reuse whichever real Tier-B-shaped rule is cheapest to
wire first -- implementer's judgment, disclose the choice in the Done
report).