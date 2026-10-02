---
id: T-0031
title: Wire frob-lease, frob-evidence, frob-tests and frob-ack verbs into the frob
  binary
state: done
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0019
- T-0020
- T-0021
parent: T-0002
tier: ticket
sprint: null
runs_last: false
milestone: 2.0.0
flavour: null
due: null
rank: null
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob-v2-wt/t-0031
branch: t-0031
scope:
- crates/frob/**
- docs/reference/**
- docs/schemas/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- cmd:cargo nextest run --profile ci -p frob-cli exit=0 sha256=e3b0c44298fc
designated_repro_test: null
acceptance:
- text: Given the frob binary, when frob --schema work, frob --schema test, frob --schema
    ack and frob ticket evidence --schema run, then each prints a schema and exits
    0
  evidence:
  - cmd:cargo nextest run --profile ci -p frob-cli exit=0 sha256=e3b0c44298fc
- text: Given a code-type ticket without measured evidence, when ticket close runs,
    then exit is 3 with the frob test remedy
  evidence:
  - cmd:cargo nextest run --profile ci -p frob-cli exit=0 sha256=e3b0c44298fc
threat: null
component: frob-bin
anchor: false
anchor_reason: null
land_commit: null
---
T-0019, T-0020 and T-0021 each expose a register(cli) function and guard implementations instead of editing crates/frob. This ticket adds the dependencies to crates/frob, calls each register, installs the evidence CloseGuard and the lease LeaseCheck into the ledger verbs, regenerates docs/reference via cargo dev gen, and adds assert_cmd tests that frob work, frob test, frob ack, frob graph and ticket evidence are reachable with --schema.