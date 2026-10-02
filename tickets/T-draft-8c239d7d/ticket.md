---
id: T-draft-8c239d7d
title: 'gob-dev: cargo dev gen for rules, directives, config reference pages and schemas;
  GEN001 check mode'
state: queued
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0006
- T-0008
- T-0014
- T-0015
parent: T-0002
tier: ticket
sprint: null
runs_last: false
milestone: 2.0.0
flavour: null
due: null
rank: null
points: 5
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
- crates/gob-dev/**
- docs/reference/**
- docs/schemas/**
- .github/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given a new rule derived in any crate, when cargo dev gen rules runs, then
    docs/reference/rules/<ID>.md appears with the doc comment explanation
  evidence: []
- text: Given a stale generated file, when cargo dev gen all --check runs, then it
    exits 1 with a diff and CI fails
  evidence: []
threat: null
component: gob-dev
anchor: false
anchor_reason: null
land_commit: null
---
Implement crates/gob-dev per documentation.md sections 2 to 3 and build-test-ci.md section 3. The cargo dev binary (never shipped) with subcommands gen rules|directives|config|schemas|all [--check], writing docs/reference/rules/<ID>.md (meta table plus explanation plus mdtest examples), docs/reference/directives.md, docs/reference/config.md (from the gob-config inventory with defaults and materialization), docs/schemas/*.json (envelope, config, ticket). --check exits 1 with a unified diff if any generated file differs (this is the GEN001 repo-local tool stage; wire it into CI). Generated files carry a header comment naming the generator. Also gen cli later; leave a stub. Use the inventory registries so adding a rule needs no edit here.