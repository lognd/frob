---
id: T-0025
title: 'Self-host switch: v2 frob.toml, import this repo''s v1 tickets, CI runs frob
  v2 check'
state: in-progress
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0024
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
worktree: /home/logan/projects/frob-v2-wt/t-0025
branch: t-0025
scope:
- frob.toml
- tickets/**
- crates/gob-dev/**
- .github/**
- CONTRIBUTING.md
- notes/coordinator.md
- .gitignore
scope_breadth_ack: true
scope_breadth_ack_reason: self-host switch imports every v1 ticket into the v2 ledger;
  tickets/** is the deliverable
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given the repository after the switch, when CI runs, then frob check and frob
    test from the v2 binary pass
  evidence: []
- text: Given the v1 tickets, when imported, then every v1 id resolves through an
    alias and the count matches
  evidence: []
threat: null
component: selfhost
anchor: false
anchor_reason: null
land_commit: null
---
Switch this repository from v1 frob to frob v2 per migration.md section 2 step 1 and D36. Write the materialized frob.toml for v2 (frob init), add a one-off script under crates/gob-dev (cargo dev import-v1-tickets) that converts tickets/T-*/ticket.md from the v1 ledger into v2 ULID tickets minted from the v1 created timestamps with aliases = ["T-0001"...], add frob check and frob test to .github/workflows/ci.yml using the built binary, remove the v1 check_base key, update CONTRIBUTING.md with the v2 workflow (work, check, test, land), and record in notes/coordinator.md that v2 is live. Record every v1-only field that could not be carried as a dropped item with reason.