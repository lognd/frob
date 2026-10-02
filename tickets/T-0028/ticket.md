---
id: T-0028
title: 'TicketField derive: generate ticket frontmatter serde, schema and docs table
  from one declaration'
state: in-progress
kind: feature
origin: agent
created: '2026-10-02'
priority: medium
blocked_by:
- T-0018
- T-0014
parent: T-0002
tier: ticket
sprint: null
runs_last: false
milestone: 2.0.0
flavour: null
due: null
rank: null
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob-v2-wt/t-0028
branch: t-0028
scope:
- crates/gob-macros/**
- crates/frob-ledger/src/schema.rs
- crates/frob-ledger/Cargo.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: crates/frob-ledger/Cargo.toml
  reason: frob-ledger gains gob-macros and inventory dependencies for the derive
  actor: logan
  at: '2026-10-02'
designated_repro_test: null
acceptance:
- text: Given the frontmatter struct with the derive, when cargo dev gen runs, then
    the ticket field reference page lists every field with its doc and default
  evidence: []
threat: null
component: gob-macros
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-0018. Add #[derive(TicketField)] (or a struct-level TicketSchema derive) to gob-macros that generates serde impls, a JSON schema and a FieldDescription inventory entry for the ticket frontmatter struct in frob-ledger, replacing the hand-written schema table T-0018 ships with. Keep the frontmatter format byte-identical.