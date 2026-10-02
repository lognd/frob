---
id: T-0017
title: 'gob-cli + frob binary: clap root, Command derive, global flags, frob doctor,
  frob init, frob config'
state: done
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0006
- T-0008
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
worktree: /home/logan/projects/frob-v2-wt/t-0017
branch: t-0017
scope:
- crates/gob-cli/**
- crates/gob-macros/**
- crates/frob/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- cmd:cargo nextest run --profile ci -p gob-cli -p frob-cli exit=0 sha256=e3b0c44298fc
designated_repro_test: null
acceptance:
- text: Given stdout is a pipe, when frob doctor runs, then output is the JSON envelope
    and exit is 0
  evidence:
  - cmd:cargo nextest run --profile ci -p gob-cli -p frob-cli exit=0 sha256=e3b0c44298fc
- text: 'Given a repo without frob.toml, when frob init runs twice, then the second
    run reports already: true and changes nothing'
  evidence:
  - cmd:cargo nextest run --profile ci -p gob-cli -p frob-cli exit=0 sha256=e3b0c44298fc
threat: null
component: frob-bin
anchor: false
anchor_reason: null
land_commit: null
---
Implement crates/gob-cli, the Command derive in gob-macros, and crates/frob (binary name frob, package name frob-cli) per cli.md sections 1 to 4 (post-D27 table) and architecture.md section 4. gob-cli: shared clap root builder taking a product name, global flags (--json, --quiet, -v, --color, --cwd, --schema, --dry-run where supported), envelope plumbing (handlers return Result<T, Refusal|Negative|Internal>, the root renders through gob-diagnostics and exits with the table), gob-log init from flags, and #[derive(Command)] that registers a verb with its summary, idempotency flag and exit-code rows into an inventory for cli reference generation. frob binary: verbs doctor (toolchain, git discovery, cache health, config materialization status, ledger ref reachability), init (write materialized frob.toml, .frob/ in .gitignore, install the ledger merge driver config per D33), config show --effective and config sync. Integration tests with assert_cmd and insta snapshots of --json output.