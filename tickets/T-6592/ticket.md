---
id: T-6592
title: 'SELFAUDIT001 SYS119: 34 templated self-audit assume entries across CWE-502/639/78/79/89/918/94
  need module-owned rewrites'
state: queued
kind: bug
origin: agent
created: '2026-09-25'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
due: null
rank: null
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
Found while working T-6528 item 5. tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations fails with 7 SELFAUDIT001 WARN findings (SYS119: templated assume): weakness:CWE-502 (2 identical), CWE-639 (2), CWE-78 (18: checker/claude_hooks/cli/core/deploy/fleet/gates/graphlang/mutate/natives/refactor/scripts_ops/serve/stratamod/testsuite/tickets_ledger/verify/vet), CWE-79 (3), CWE-89 (3), CWE-918 (3), CWE-94 (6: cli/core/gates/graphlang/stratamod/tickets_ledger) -- 34 assume entries total, each currently copy-pasted across modules with only the node name substituted. Each needs a real, module-owned assume naming that module's own concrete mechanism or evidence gap, not a template. This is content-writing across the design/strata self-model corpus (which module actually owns each CWE's mitigation reasoning), not a small verifiable code fix -- too broad for T-6528's own drain-triage pass; filing as its own dedicated pass. Scope: the strata design/self-model source that declares each module's assume entries (see frob.strata's design-loading code for the exact file(s)).