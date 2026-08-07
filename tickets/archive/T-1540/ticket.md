---
id: T-1540
title: 'PERF012 registry-entry gap: detector exists with no CHK-GATE-PERF012 row'
state: dropped
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
PERF012 fires from src/frob/perf but docs/design/registry/check-coverage.yaml has no CHK-GATE-PERF012 entry -- pre-existing gap found (not caused) by T-1225's PERF01x work. Originally tracked as worktree draft T-draft-7858da45, which the tickets.md splice drops from merge previews (land-splice-regression class), so refiled as a real ticket.

## Drop reason
- 2026-08-05: duplicate of T-1539: both are refiles of the same PERF012 registry-gap draft lost to the ledger-splice corruption; T-1539 is the survivor