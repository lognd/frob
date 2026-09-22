---
id: T-5179
title: 'REG002: 18 check-coverage.yaml dispositions name gate rules absent from the
  live rule registry (RACE001, TESTMOCK001, CONFIGPATH001, ROUTE001, INV010/011, WRAP001-003,
  COV010, ...)'
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: high
parent: null
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
- docs/design/registry/check-coverage.yaml
- src/frob/gates/_registry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-09-21 05:05, frob check --base dev on dev after the overnight land drain: 18 REG002 errors, one per CHK-GATE-<RULE> entry whose disposition handled_by:<RULE> names a rule the live gate/policy registry does not know: BASE001, CLAIM001, CONFIGPATH001, COV010, GUARD001, INV010, INV011, PII013, RACE001, RACE002, REL303, ROUTE001, SYS114, SYS115, TESTMOCK001, WRAP001, WRAP002, WRAP003. Most of these rules landed tonight (T-3953 RACE001, T-3997 TESTMOCK001, T-4114 CONFIGPATH001, T-4115 ROUTE001, T-3962 INV011, T-4760 WRAP00x, T-4254 COV010 ...) with their coverage entries but without an entry in the registry the REG002 check consults (_KNOWN_GATE_RULES in frob.gates._waive, or the T-4661 gate registry's derived view). Land's UnregisteredGateRuleConstructed guard did not catch them, so that guard's 'constructs a rule id' detection and REG002's registry view disagree about what registered means. Fix: register every listed rule where REG002 looks (and make the land guard and REG002 read the same registry so this cannot recur); add a test that every handled_by target in check-coverage.yaml resolves. Verify with frob check --base dev: REG002 count 18 -> 0.