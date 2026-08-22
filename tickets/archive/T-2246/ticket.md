---
id: T-2246
title: Audit test-only quarantine seed helpers for WIRE001 exemption vs deletion
state: done
kind: docs
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/verify/test_quarantine.py
- tests/unit/verify/test_verify_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/verify/test_verify_runner.py
  reason: 'T-2246: both waivers citing this ticket as WIRE002''s live-open-ticket
    follow_up need re-pointing to permanent="true" (docs/modules/gates.md''s own WIRE001/WIRE002
    T-1592 precedent for a private test-seed helper with no production caller by design)
    so this ticket can actually close -- tests/unit/verify/test_verify_runner.py::_seed_identity_less_store
    is the sibling waiver, same shape as this ticket''s own scoped _seed_stuck_store'
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/verify/test_quarantine.py::TestIdentityLessFindingRecovery::test_retire_unidentifiable_findings_recovers_a_stuck_store
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 4c6850a5eeb3d5be92ef856a0b3545100826589a
---
frob:waive WIRE001 on tests/unit/verify/test_quarantine.py::_seed_stuck_store needs a live open follow_up ticket (WIRE002) but has no real wiring work pending -- it is a permanent test-only fixture helper, never meant to gain a production caller. Filed only to satisfy WIRE002's live-ticket requirement (T-2217's own land discovered this); either confirm the waiver's reasoning is permanent and this ticket can close as-is, or delete the helper if it turns out unused.