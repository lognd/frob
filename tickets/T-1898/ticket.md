---
id: T-1898
title: Register CHK-GATE-TEST019 in check-coverage.yaml (T-1877 follow-up)
state: dropped
kind: bug
origin: human
created: '2026-08-09'
priority: medium
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
T-1877 added TEST019 (frob.gates._test019_deflated_symbols, frob:enforces CHK-GATE-TEST019) but could not add the matching CHK-GATE-TEST019 entry to docs/design/registry/check-coverage.yaml because that file was held by a live cross-worktree lease from T-1888 at the time. REG009 is waived on the new frob:enforces directive with a reason pointing at this ticket. Once T-1888 lands/releases the lease, add a CHK-GATE-TEST019 entry to check-coverage.yaml dispositioned handled_by:TEST019 (same shape as the existing TEST018/TEST017 entries) so the waiver can be removed.

## Drop reason
- 2026-08-09: Superseded: the CHK-GATE-TEST019 registry entry was added directly in T-1877 itself once T-1888's lease cleared, and the REG009 waiver was removed
