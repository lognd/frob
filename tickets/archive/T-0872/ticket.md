---
id: T-0872
title: 'arch warning burn-down: gate:ARCH to zero unwaived (72 warns baseline) + suggestion
  sweep'
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
- text: GIVEN the repo at this ticket's close WHEN frob check runs THEN gate:ARCH
    reports zero unwaived warnings and every remaining waiver carries a current, specific
    reason
  evidence: []
threat: null
component: arch
---
T-0204 child (arch family). gate:ARCH reports 72 warnings (13 waived) + frob-arch 55 warnings/183 suggestions at 2026-07-23 baseline (recount at start). Triage every warning: fix the code (long-function/god-class residue, calibrated-threshold stragglers) or waive with a specific reason per T-0289 doctrine. Suggestions: sweep for real fixes; remainder must be explainable. Deliverable: gate:ARCH 0 unwaived warnings and the summary line honest.

## Drop reason
- 2026-07-27: superseded by the T-0399 promotion audit's counted ARCH burn-down (T-0970, 101 findings measured 2026-07-27) (absorbed by T-0970)