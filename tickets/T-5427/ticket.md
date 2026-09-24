---
id: T-5427
title: SYS119 templated-assume burn-down (CWE-502/639/78/89/918/94, 35 node-instances)
  blocks test_sys_gate_zero_violations
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
worktree: null
branch: null
scope:
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: found while draining CI run 35951365410 self-gate clusters; flagging duplicate
    pair, not merging myself
  actor: logan
  at: '2026-09-24'
  old_length: 979
  new_length: 1216
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-5396 (distinct from T-5214, the narrative SYS003/SYS100/SYS110 gap this ticket already fixed): tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations asserts violations == () (zero tolerance, WARN included), but design/frob.strata carries 6 pre-existing SYS119 templated-assume WARN groups (35 node-instances): CWE-502 (testsuite, vet), CWE-639 (graphlang, vet), CWE-78 (18 nodes), CWE-89 (graphlang, testsuite, vet), CWE-918 (cli, testsuite, vet -- T-5396 added the cli member), CWE-94 (cli, core, gates, graphlang, stratamod, tickets_ledger). find_templated_assumes tokenizes the PARSED claim fields, not the prose comment above the assume -- a real fix embeds a concrete module-specific mechanism into the claim id itself, per T-5105's own test_genuinely_specific_assume_not_reported. Caution: T-5396 found suffixing a claim id can break THREAT003/DOC003's discharge-matching -- re-verify before assuming a suffix is free.

Note: T-5425 duplicates this ticket (same SYS119 templated-assume burn-down, same scope design/frob.strata, same 6 groups/35 node-instances) -- the next owner should dedupe (close one as a duplicate of the other) rather than work both.