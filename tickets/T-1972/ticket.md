---
id: T-1972
title: 'REG010: file CHK-GATE-SYS110 in docs/design/registry/check-coverage.yaml'
state: queued
kind: docs
origin: human
created: '2026-08-10'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/design/registry/check-coverage.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1629 added live gate rule SYS110 (frob.strata._selfconform). frob check --only registry warns REG010: no CHK-GATE-SYS110 entry exists in check-coverage.yaml. File one (handled_by:SYS110, matching the CHK-GATE-SYS108/SYS109 precedent) and add a frob:enforces CHK-GATE-SYS110 edge if REG008 also wants one.

## Failure log
- 2026-08-10 attempt 1: already resolved: T-1629's own land (7b1f55513) added the CHK-GATE-SYS110 entry to check-coverage.yaml; frob check --only registry is clean (0 errors) for SYS110. REG010 must have been a stale/pre-check read; no code change needed. Only DOCENUM001 (docs/modules/gates.md enumerates list) was actually missing, fixed separately as T-1978.
