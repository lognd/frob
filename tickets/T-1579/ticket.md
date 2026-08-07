---
id: T-1579
title: 'WAIVE004 auto-fix: mass-stale states can never self-heal -- add detector-proven
  escape from the count guard'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
blocked_by:
- T-1620
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine.py
- docs/modules/gates.md
- docs/design/check-fix-engine.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestWaive004DegradedRunGuard::test_mass_invalidation_with_live_finding_elsewhere_proceeds
designated_repro_test: null
threat: null
component: null
---
The T-1323 mass-invalidation guard refuses to delete when >= 5 waivers of one rule go stale in one run. Correct for degraded runs -- but it also means a rule whose waivers become GENUINELY mass-stale (detector tightened, mass refactor) is permanently uncleanable: every run re-flags them, the auto-fix always refuses, warnings never drain. The guard cannot currently tell 'detector died' from 'detector ran and they really are all stale'.

Refinement: when the SAME self-manufactured run produced >= 1 live finding of the target rule elsewhere in the tree, the detector demonstrably ran and can find that rule -- mass-staleness is then trustworthy, and deletion may proceed (still capped per run, still one rule at a time, still logged per waiver). When the rule has ZERO findings anywhere (the degraded signature, exactly what T-1578's structural signal also targets), keep refusing as today. Depends on T-1578 conceptually but is independently implementable; blocked_by is intentionally not set.