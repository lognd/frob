---
id: T-0393
title: 'advisories: triage abstraction-opportunity near-dup families'
state: dropped
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: T-0376
tier: ticket
sprint: null
scope:
- src/frob/
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Triage the 37 frob-arch abstraction-opportunity advisories: for each genuine near-duplicate or specific-signature family, either extract the real shared code into one home, or add an explicit reason-note accepting the duplication. Acceptance: frob check arch advisories for abstraction-opportunity reduced to zero unresolved (each is either fixed or reason-noted).

## Drop reason
- 2026-07-28: absorbed: its decomposition landed in full -- T-1068 (detector language-parity precision, 5beeed09) + T-1067 (per-package extraction pass, 3da9178d); the advisory bucket this ticket tracked is now measured and worked at the successor granularity