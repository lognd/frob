---
id: T-5425
title: 'SYS119 templated-assume burn-down: 6 groups / 35 node-instances in design/frob.strata
  block test_sys_gate_zero_violations'
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
- design/frob.strata
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
Found while working T-5396: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations asserts violations == () (zero tolerance, including WARN), but design/frob.strata carries 6 pre-existing SYS119 templated-assume WARN groups (35 node-instances total, unrelated to T-5396's narrative/capability fixes): CWE-502 (testsuite, vet), CWE-639 (graphlang, vet), CWE-78 (18 nodes: checker, claude_hooks, cli, core, deploy, fleet, gates, graphlang, mutate, natives, refactor, scripts_ops, serve, stratamod, testsuite, tickets_ledger, verify, vet), CWE-89 (graphlang, testsuite, vet), CWE-918 (cli, testsuite, vet -- T-5396 added the cli member), CWE-94 (cli, core, gates, graphlang, stratamod, tickets_ledger). find_templated_assumes (src/frob/strata/_assume_template.py) tokenizes the PARSED claim fields (id, body type, src/dst, owner, review) -- NOT the // prose comment above the assume -- so an id/reason 'genuinely specific' fix per T-5105's own test (test_genuinely_specific_assume_not_reported) means embedding a concrete, module-specific mechanism/evidence-gap into the claim id itself (e.g. 'weakness:CWE-78:vet:validated-via-shlex-quote-and-allowlist'), not just prose. Caution: for a node reachable from 'registry', changing the assume id string may also need re-verifying against THREAT003's own discharge-matching logic (T-5396 found DOC003 fails to match a suffixed id in at least one shape -- re-check whether the discharge join is by exact id or by (CWE, node) pair before assuming a suffix is free).