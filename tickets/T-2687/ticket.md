---
id: T-2687
title: Recovered from T-2134's phantom TICK006 citation of T-draft-f3bbfd8e
state: dropped
kind: bug
origin: agent
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2134's Done report claimed T-draft-f3bbfd8e was filed, but T-draft-f3bbfd8e resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> :test_v2_mode_repo_with_a_lingering_monofile_errors, tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_is_silent
Filed: T-draft-f3bbfd8e (gates: QueueUnavailable manufactures an
empty-rule-id finding against the retired tickets.md path -- real id
after land)

### Change

## Drop reason
- 2026-08-19: Measured (T-2690 series triage): cites T-draft-f3bbfd8e, which git history confirms was renamed (git show -M --name-status 946c41ac1: R100 tickets/T-draft-f3bbfd8e/ticket.md -> tickets/T-2684/ticket.md) to the real, live ticket T-2684 ('gates: QueueUnavailable manufactures an empty-rule-id finding against the retired tickets.md path', state=queued, full correct body, already had its own citation bug fixed this session). T-2687's own body is a garbled truncated fragment of the same underlying finding T-2684 already tracks correctly -- a bookkeeping duplicate, not independent work. Root mechanism (the auto-recovery mechanism that filed T-2687 without checking git rename history first) fixed in T-2690.
