---
id: T-5767
title: 'LAYOUT001-00x: render-exists, review-current (source_hash), unreviewed=fail'
state: done
kind: feature
origin: human
created: '2026-09-24'
priority: medium
blocked_by:
- T-5764
parent: T-5747
tier: ticket
sprint: layout-gate
runs_last: false
milestone: v0.537.0
flavour: null
due: null
rank: null
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5767
branch: t-5767
scope:
- src/frob/gates/_layout_gate.py
- src/frob/webapp/_layout_structure.py
- tests/unit/test_layout_gate.py
- tests/fixtures/webapp/layout1xx/
- docs/modules/webapp-layout-structure.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_layout_gate.py
  reason: unit tests for LAYOUT001-003 gate
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/fixtures/webapp/layout1xx/
  reason: gallery manifest fixtures for LAYOUT gate tests
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/webapp-layout-structure.md
  reason: LAYOOUT001-003 rule doc
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
evidence:
- tests/unit/test_layout_gate.py::test_recompute_source_hash_matches_props_less_compute_source_hash
- tests/unit/test_layout_gate.py::test_unreviewed_entry_raises_layout001
- tests/unit/test_layout_gate.py::test_stale_hash_raises_layout002
- tests/unit/test_layout_gate.py::test_reviewed_current_entry_is_clean
- tests/unit/test_layout_gate.py::test_missing_artifacts_raises_layout003
- tests/unit/test_layout_gate.py::test_gate_discovers_hook_and_scans_manifest
- tests/unit/test_layout_gate.py::test_gate_returns_empty_with_no_manifest_files
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
LAYOUT001-00x rules: render-exists, review-current (manifest source_hash matches current source and fixture props byte hash, owner decision Q3), unreviewed (verdict null) = fail. New gate module reusing the A11Y auto-discovery pattern.

Positive control: a fixture manifest entry with source_hash mismatch vs current file content raises LAYOUT002; a verdict=null entry raises LAYOUT001; both clear once real.

Doc page: docs/modules/webapp-layout-structure.md

Cross-repo dependency: blocked on the crunk repo leaf titled 'Define versioned gallery manifest JSON schema' (crunk epic 'gallery: every component and layout rendered and reviewed en masse'). Ids differ across repos, so the edge is recorded here by title.

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/CRUNK-GALLERY-TREE.md (sections 2 and 5; section 5 overrides).