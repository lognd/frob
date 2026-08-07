---
id: T-1775
title: T-1763's land silently re-added CHK-GATE-INV006 to check-coverage.yaml via
  Tier-A REG010 sync, main is REG002-red
state: in-progress
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/check-coverage.yaml
- src/frob/gates/_fix_engine_sync.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_new_error_fixed_by_tier_a_lands_with_a_followup_commit
designated_repro_test: null
threat: null
component: null
---
T-1763 deleted INV006 and removed its CHK-GATE-INV006 registry row (docs/design/registry/check-coverage.yaml), verified via frob check --land-parity clean multiple times pre-land. The land itself (frob ticket land T-1763) ran its own pre-land Tier-A auto-fix pass (fix_reg010_registry_sync, logged as '2 fix(es) applied' each attempt) which silently RE-ADDED CHK-GATE-INV006 with gate_rule_total bumped back to 289, and that state is what actually landed on main (verified: git show main:docs/design/registry/check-coverage.yaml shows CHK-GATE-INV006 present, gate_rule_total: 289). Main is currently REG002-red: 'CHK-GATE-INV006 disposition handled_by:INV006 names a rule that does not exist in the live gate/policy rule registry' (verified via frob check --only registry against current main). Root cause candidate: fix_reg010_registry_sync's known_gate_rule_ids() read during land's pre-land Tier-A pass ran against a stale/not-yet-rebuilt native or cached module state that still considered INV006 known, re-adding the row a moment after the worktree-side fix had already removed it -- this reverted a full ~4 times across separate land attempts in the same session, always exactly reverting to 289/present. Fix: remove CHK-GATE-INV006 again (gate_rule_total -> 288) and investigate why fix_reg010_registry_sync's pre-land run disagreed with a fresh worktree-side check; consider whether the Tier-A sync should re-run AFTER the native rebuild step, not before/concurrently with it.