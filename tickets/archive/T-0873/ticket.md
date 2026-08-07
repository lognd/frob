---
id: T-0873
title: 'perf warning burn-down + waiver re-audit: gate:PERF to zero unwaived (24 warns,
  29 waivers baseline)'
state: dropped
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN the repo at this ticket's close WHEN frob check runs THEN gate:PERF
    reports zero unwaived warnings and every remaining waiver has been re-verified
    with a current reason
  evidence: []
threat: null
component: perf
---
T-0204 child (perf family). gate:PERF reports 24 warnings + 29 waived at 2026-07-23 baseline (recount at start). Fix the unwaived findings; re-audit every standing waiver still holds after the T-0161-era heuristic fixes (drop stale waivers, re-reason keepers). Deliverable: gate:PERF 0 unwaived warnings, all waivers re-verified with current reasons.

## Drop reason
- 2026-07-27: superseded by the T-0399 promotion audit's counted PERF burn-down (T-0972, 1730 findings measured 2026-07-27) (absorbed by T-0972)