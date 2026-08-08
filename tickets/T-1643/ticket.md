---
id: T-1643
title: Wire a real Tier-B --fix handler (T-1262 shipped only the synthetic TIERBDEMO001
  reference handler)
state: done
kind: feature
origin: agent
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine_tier_b.py
- src/frob/gates/_fix_engine.py
- tests/test_gates.py
- docs/design/check-fix-engine.md
- design/frob.strata
- tickets/T-1643/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/design/check-fix-engine.md
  reason: 'AFFECT001: doc anchor for TIER_B_HANDLERS/new handler; SELFAUDIT001: new
    public symbol needs interface sync via frob sys sync-interface'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: design/frob.strata
  reason: 'AFFECT001: doc anchor for TIER_B_HANDLERS/new handler; SELFAUDIT001: new
    public symbol needs interface sync via frob sys sync-interface'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1643/**
  reason: 'SCOPE001: ticket''s own per-ticket ledger file, per T-1742/T-1737/T-1483
    precedent'
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_gates.py::TestFixEngineTierB::test_dead001_removes_unreferenced_private_symbol
- tests/test_gates.py::TestFixEngineTierB::test_dead001_skips_a_waived_finding
- tests/test_gates.py::TestFixEngineTierB::test_dead001_at_most_one_deletion_per_file_per_pass
designated_repro_test: null
threat: null
component: null
---
T-1262's own Done report discloses this as a cut, out of its declared scope: fix_tierbdemo001_marker_rewrite is a deliberately synthetic handler (keyed to a placeholder TIERBDEMO001 id that is never a real frob check rule) proving the snapshot-apply-verify-commit-or-rollback transaction path end-to-end. No real, production Tier-B handler (a handler for an actual gate rule id) exists yet. Pick a real candidate rule currently fixed only at Tier A or not auto-fixed at all, and wire it through the Tier-B transaction machinery T-1262 built, following that ticket's own TIER_B_HANDLERS registration precedent.