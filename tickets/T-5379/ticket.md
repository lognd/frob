---
id: T-5379
title: 'test_every_may_is_load_bearing: 24 non-load-bearing ''may'' mutation findings
  on live repo design'
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/strata/test_mutation_audit.py
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
CI run 35819358270 (ubuntu/macos/windows); re-verified failing on dev tip 39b89ed091: tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_every_may_is_load_bearing fails -- run_may_mutation_audit(repo_root) reports 24 findings where deleting or substituting a design 'may' atom does not trip SYS100 (and where required, the SYS100+SYS101 pair), e.g. node='testsuite' atom='process-control' mode='substitute' sys100_fired=True sys101_fired=False. Each finding needs either a real enforcing check wired up for that atom or the design declaration corrected/removed. Not covered by any open ticket found by title/body search; needs per-atom triage, not a single fix.