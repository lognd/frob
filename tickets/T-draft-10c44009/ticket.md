---
id: T-draft-10c44009
title: 'gob-config: ConfigTable derive, layered load, materialized knobs, CFG001'
state: queued
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0005
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
- crates/gob-config/**
- crates/gob-macros/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given a frob.toml missing a materialized knob, when check runs, then CFG001
    names the key, the default, and the fix command
  evidence: []
- text: Given a frob.toml with comments, when materialize adds knobs, then existing
    comments and order are preserved (snapshot)
  evidence: []
- text: Given an unknown key, when loaded, then the error names the key and the nearest
    valid key
  evidence: []
threat: null
component: gob-config
anchor: false
anchor_reason: null
land_commit: null
---
Implement crates/gob-config and the ConfigTable derive in gob-macros per architecture.md section 6 (config), goals.md principle no invisible variables, D22, D34. Features: #[derive(ConfigTable)] with #[config(table = "tickets", materialize)] and per-field #[config(default = ..., doc from doc comment, enforcement = true)]; a Config loader that reads <product>.toml from the repo root (product name is a parameter, frob.toml for frob), applies layering (defaults < file < explicit CLI overrides passed as a map) and reports unknown keys as errors with a did-you-mean; a materialize function that writes every enforcement knob that is absent from the file with its default and a doc comment, used by frob init, and a check function that returns one CFG001 finding per missing materialized knob (rule declared here with #[derive(Rule)]); a JSON schema export of the whole config (schemars) for frob schema; an inventory of tables so gob-dev can generate the config reference page. Use toml_edit to preserve comments and ordering when materializing. Tests with insta snapshots of materialized output.