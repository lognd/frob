---
id: T-draft-7ae602e1
title: 'SYSDESIGN301: outbound call sets a fresh fixed timeout instead of deriving
  from the inbound deadline'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-draft-ce656788
tier: ticket
sprint: sysdesign
runs_last: false
milestone: 0.539.0
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
- src/frob/strata/_deadline_propagation.py (new)
- tests/fixtures/sysdesign/sysdesign301/**
scope_breadth_ack: true
scope_breadth_ack_reason: sysdesign epic tree, scope reviewed by coordinator
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN301: outbound call sets a fresh fixed timeout instead of deriving from the
       inbound request's remaining deadline
kind: feature
tier: leaf
parent: T-SYS-SE
milestone: 0.539.0
sprint: sysdesign
points: 3
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/strata/_deadline_propagation.py (new), docs/modules/gates.md
       (SYSDESIGN301 row), tests/fixtures/sysdesign/sysdesign301/**
blocked_by: [T-SYS-A-FLOW-TIMEOUT-FIX]
tag: Static: code

Research row 6.9: Google SRE Book, "Addressing Cascading Failures", https://sre.google/
sre-book/addressing-cascading-failures/ (fetched; the retries section models per-hop RPC
timeout as `grpc.WithTimeout(5 * time.Second)` without deadline propagation as the flagged
anti-pattern). Lint condition: "An RPC client that sets a fresh fixed timeout per outbound
call instead of deriving from the inbound request's remaining deadline flags (this is exactly
the naive-retry scenario the SRE book models as destabilizing)."

Inventory finding (SYSDESIGN-INVENTORY.md): "PARTIAL. REL200/REL201 give per-flow `timeout` (a
deadline at one hop), and REL272 gives cross-hop `correlation` (trace-id propagation), but no
rule explicitly checks that a deadline/remaining-budget is propagated hop-to-hop." Blocked_by
T-SYS-A-FLOW-TIMEOUT-FIX because that ticket resolves whether `Flow.timeout` is fed by grammar
or by attr -- this rule must read whichever mechanism is confirmed live.

Acceptance criteria: for a multi-hop synchronous chain (per REL340's existing sync-depth
tracking), flags an outbound client call whose timeout literal is not derived from (does not
reference) the parent request's remaining deadline. Positive-control fixture: tests/fixtures/
sysdesign/sysdesign301/fresh-timeout-per-hop/**.
