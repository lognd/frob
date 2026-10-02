---
id: T-0011
title: 'gob-walk + gob-cache: ignore-aware walk, SQLite artifact and findings cache'
state: done
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0004
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
worktree: /home/logan/projects/frob-v2-wt/t-0011
branch: t-0011
scope:
- crates/gob-walk/**
- crates/gob-cache/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- cmd:cargo nextest run --profile ci -p gob-walk -p gob-cache exit=0 sha256=e3b0c44298fc
designated_repro_test: null
acceptance:
- text: Given a repo with .gitignore excluding target/, when walked, then no path
    under target/ appears and the order is stable across runs
  evidence:
  - cmd:cargo nextest run --profile ci -p gob-walk -p gob-cache exit=0 sha256=e3b0c44298fc
- text: Given a findings entry keyed by (digest, rule, version, side-input), when
    any key component changes, then the lookup misses
  evidence:
  - cmd:cargo nextest run --profile ci -p gob-walk -p gob-cache exit=0 sha256=e3b0c44298fc
threat: null
component: gob-cache
anchor: false
anchor_reason: null
land_commit: null
---
Implement crates/gob-walk and crates/gob-cache per architecture.md section 3 and D30. gob-walk: parallel repository walk with the ignore crate honoring .gitignore and a [check] exclude knob, returning FileEntry { path, size, blake3 digest, language guess by extension } in a deterministic order; size cap knob with Unresolved marker for oversized files. gob-cache: per-worktree SQLite at .frob/cache.sqlite (WAL, busy_timeout knob, best-effort writes logged on failure, schema versioned with migrations): tables artifacts(key = digest + producer identity, bytes), findings(file digest, rule id, rule version, side-input digest -> serialized findings), repo_rule(graph digest, rule id -> findings). API is sync; a Cache::open fails soft (returns a NullCache) when the directory is read-only. Benchmarks with criterion for walk of 10k files and 10k cache hits.