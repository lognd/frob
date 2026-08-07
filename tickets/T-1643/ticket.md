---
id: T-1643
title: Wire a real Tier-B --fix handler (T-1262 shipped only the synthetic TIERBDEMO001
  reference handler)
state: queued
kind: feature
origin: agent
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine_tier_b.py
- src/frob/gates/_fix_engine.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1262's own Done report discloses this as a cut, out of its declared scope: fix_tierbdemo001_marker_rewrite is a deliberately synthetic handler (keyed to a placeholder TIERBDEMO001 id that is never a real frob check rule) proving the snapshot-apply-verify-commit-or-rollback transaction path end-to-end. No real, production Tier-B handler (a handler for an actual gate rule id) exists yet. Pick a real candidate rule currently fixed only at Tier A or not auto-fixed at all, and wire it through the Tier-B transaction machinery T-1262 built, following that ticket's own TIER_B_HANDLERS registration precedent.