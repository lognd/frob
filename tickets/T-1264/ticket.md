---
id: T-1264
title: 'gates --fix fixability registry field: generated-verified auto/verified/assisted/manual
  tier per rule id'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
blocked_by:
- T-1262
- T-1263
- T-1261
parent: T-1137
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fixability_scan.py
- src/frob/gates/__init__.py
- docs/design/registry/check-coverage.yaml
- src/frob/registry/_staleness.py
- tests/test_gates.py
- docs/design/check-fix-engine.md
- docs/design/registry/EXHAUSTIVENESS-GATE.md
- tickets/T-1264/ticket.md
- design/frob.strata
- tests/test_registry_staleness.py
- tickets/T-1264/done-report.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/design/check-fix-engine.md
  reason: 'AFFECT001: touched both docs to describe the now-implemented fixability
    field (previously a design-only proposal section)'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/design/registry/EXHAUSTIVENESS-GATE.md
  reason: 'AFFECT001: touched both docs to describe the now-implemented fixability
    field (previously a design-only proposal section)'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1264/ticket.md
  reason: own ticket record; ticket-mutating CLI commits touch it as part of normal
    workflow
  actor: logan
  at: '2026-08-08'
- op: add
  glob: design/frob.strata
  reason: 'SELFAUDIT001/SYS104: new public symbols (generated_fixability, FixabilityConflict,
    sync_gate_rule_fixability) need declared interface entries'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_registry_staleness.py
  reason: sync_gate_rule_entries now also backfills fixability on already-in-sync
    files (acceptance 3); existing fixture assertion needs updating
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1264/done-report.md
  reason: own done-report file, written by frob ticket done-report CLI
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_gates.py::TestRuleFixability::test_every_known_rule_id_maps_to_exactly_one_tier
- tests/test_gates.py::TestRuleFixability::test_conflicting_registration_raises_fixabilityconflict
- tests/test_gates.py::TestRuleFixability::test_checked_in_literal_matches_a_fresh_scan
- tests/test_gates.py::TestRuleFixability::test_sync_gate_rule_fixability_backfills_missing_field
- tests/test_registry_staleness.py::TestSyncGateRuleEntries::test_already_in_sync_returns_empty_tuple
designated_repro_test: null
acceptance:
- text: GIVEN every known gate rule id THEN generated_fixability() maps it to exactly
    one of auto/verified/assisted/manual, with manual as the correct default for a
    rule with no handler in any table
  evidence:
  - tests/test_gates.py::TestRuleFixability::test_every_known_rule_id_maps_to_exactly_one_tier
- text: GIVEN a rule id registered in more than one of TIER_A_HANDLERS/TIER_B_HANDLERS/TIER_C_EMITTERS
    WHEN generated_fixability() runs THEN it raises FixabilityConflict rather than
    silently picking one
  evidence:
  - tests/test_gates.py::TestRuleFixability::test_conflicting_registration_raises_fixabilityconflict
- text: GIVEN the checked-in _KNOWN_RULE_FIXABILITY literal WHEN it drifts from a
    fresh generated_fixability() scan (a handler added without updating the literal)
    THEN TestRuleFixability fails loud
  evidence:
  - tests/test_gates.py::TestRuleFixability::test_checked_in_literal_matches_a_fresh_scan
- text: 'GIVEN check-coverage.yaml''s CHK-GATE-<rule> entries THEN each carries a
    fixability: field kept in sync the same idempotent way gate_rule_entries already
    is'
  evidence:
  - tests/test_gates.py::TestRuleFixability::test_sync_gate_rule_fixability_backfills_missing_field
threat: null
component: null
---
Build the generated-verified fixability registry field per
docs/design/check-fix-engine.md "Fixability registry field" section,
mirroring src/frob/gates/_rule_id_scan.py's own generated-verified shape
(scanner is authority, checked-in literal is generated artifact,
drift-lock test re-verifies every run). New
src/frob/gates/_fixability_scan.py: generated_fixability() imports
TIER_A_HANDLERS (_fix_engine.py), TIER_B_HANDLERS (_fix_engine_tier_b.py),
TIER_C_EMITTERS (_fix_engine_tier_c.py), and known_gate_rule_ids()
(_rule_id_scan.py), and maps every known rule id to auto/verified/
assisted/manual -- raising FixabilityConflict if a rule id appears in
more than one table. Add the checked-in _KNOWN_RULE_FIXABILITY literal
(frob.gates.__init__ or a similarly central module) plus
tests/test_gates.py::TestRuleFixability re-verifying it against a fresh
scan. Extend docs/design/registry/check-coverage.yaml's CHK-GATE-<rule>
entries with a fixability: field, synthesized the same idempotent way
sync_gate_rule_entries already synthesizes missing entries (reuse that
function's shape, do not invent a second YAML-mutation pattern).