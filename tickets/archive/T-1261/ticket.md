---
id: T-1261
title: 'gates --fix Tier-A batch 2: fmt/registry-regen/release-sync/WAIVE004 handlers'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1137
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine.py
- tests/test_gates.py
- src/frob/gates/_waive.py
- src/frob/release/**
- docs/modules/gates.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_waive.py
  reason: WAIVE004 handler reads _waive.py's full-run detection; release-sync handler
    calls existing release sync machinery
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/release/**
  reason: WAIVE004 handler reads _waive.py's full-run detection; release-sync handler
    calls existing release sync machinery
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/modules/gates.md
  reason: AFFECT001/COV001 gate remedies for this ticket's new Tier-A handler symbols
    require touching the affects()-closure doc in the same diff
  actor: logan
  at: '2026-07-29'
- op: add
  glob: design/frob.strata
  reason: SYS104 interface= entries for this ticket's new public symbols (TIER_A_HANDLERS
    + four handler functions) require touching the .strata interface declarations
    in the same diff
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_gates.py::TestFixEngineTierABatch2::test_fmt001_wraps_overlong_directive_line_and_reverifies_clean
- tests/test_gates.py::TestFixEngineTierABatch2::test_fmt001_already_canonical_is_a_no_op
- tests/test_gates.py::TestFixEngineTierABatch2::test_reg010_files_missing_entries_and_reverifies_clean
- tests/test_gates.py::TestFixEngineTierABatch2::test_reg010_already_in_sync_is_a_no_op
- tests/test_gates.py::TestFixEngineTierABatch2::test_rel002_resyncs_pyproject_and_uv_lock_from_manifest
- tests/test_gates.py::TestFixEngineTierABatch2::test_rel002_already_in_sync_touches_nothing
- tests/test_gates.py::TestFixEngineTierABatch2::test_waive004_removes_stale_waiver_on_a_full_unscoped_run
- tests/test_gates.py::TestFixEngineTierABatch2::test_waive004_refuses_a_scoped_run
- tests/test_gates.py::TestFixEngineTierABatch2::test_waive004_leaves_a_multi_line_continued_waiver_alone
designated_repro_test: null
acceptance:
- text: GIVEN an E501 finding on a line carrying a frob:waive comment WHEN --fix runs
    THEN frob fmt is invoked and the line re-verifies clean
  evidence:
  - tests/test_gates.py::TestFixEngineTierABatch2::test_fmt001_wraps_overlong_directive_line_and_reverifies_clean
  - tests/test_gates.py::TestFixEngineTierABatch2::test_fmt001_already_canonical_is_a_no_op
- text: GIVEN a REG008/REG010 missing gate_rule_entries finding WHEN --fix runs THEN
    sync_gate_rule_entries regenerates the missing entries and REG010 re-verifies
    clean
  evidence:
  - tests/test_gates.py::TestFixEngineTierABatch2::test_reg010_files_missing_entries_and_reverifies_clean
  - tests/test_gates.py::TestFixEngineTierABatch2::test_reg010_already_in_sync_is_a_no_op
- text: GIVEN a REL002 version-quartet mismatch WHEN --fix runs THEN the existing
    release sync path regenerates the three derived artifacts from the manifest and
    REL002 re-verifies clean, with pyproject.toml/CHANGELOG.md/uv.lock never hand-edited
  evidence:
  - tests/test_gates.py::TestFixEngineTierABatch2::test_rel002_resyncs_pyproject_and_uv_lock_from_manifest
  - tests/test_gates.py::TestFixEngineTierABatch2::test_rel002_already_in_sync_touches_nothing
- text: GIVEN a WAIVE004 finding produced by a genuine full unscoped frob check run
    WHEN --fix runs THEN the stale frob:waive line is removed and WAIVE004 re-verifies
    clean; GIVEN the same finding from a --only/--ticket-scoped run THEN --fix refuses
    to act on it and leaves the waiver untouched
  evidence:
  - tests/test_gates.py::TestFixEngineTierABatch2::test_waive004_removes_stale_waiver_on_a_full_unscoped_run
  - tests/test_gates.py::TestFixEngineTierABatch2::test_waive004_refuses_a_scoped_run
  - tests/test_gates.py::TestFixEngineTierABatch2::test_waive004_leaves_a_multi_line_continued_waiver_alone
threat: null
component: null
---
Add four more Tier-A handlers to src/frob/gates/_fix_engine.py (same
protocol as the four T-1138/T-1177 already ship): frob fmt invocation for
E501-on-waive-line findings (frob fmt is already idempotent, calling it
IS the fix -- no new rewrite logic), generated-registry regeneration for
REG008/REG010 (call frob.registry._staleness.sync_gate_rule_entries,
already exists), release sync for REL002 (call the existing frob release
sync machinery, never hand-bump), and WAIVE004 full-run-verified
stale-waiver removal (delete the frob:waive line ONLY when the run that
produced the finding was a genuine full unscoped run, mirroring
_waive.py's own "trust this only from a full run" disclaimer -- refuse to
act on a --only/--ticket-scoped run's WAIVE004 output). Register each in
an explicit TIER_A_HANDLERS: dict[str, TierAHandler] alongside the
existing four (promoting apply_tier_a_fixes's current positional-call
list to a dict keyed by rule id, per docs/design/check-fix-engine.md's
"Fix-handler protocol" section, so the fixability-registry-field ticket
has a real table to scan).