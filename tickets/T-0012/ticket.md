---
id: T-0012
title: 'gob-languages: tree-sitter rust, markdown, toml behind features'
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
worktree: /home/logan/projects/frob-v2-wt/t-0012
branch: t-0012
scope:
- crates/gob-languages/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- cmd:cargo nextest run --profile ci -p gob-languages exit=0 sha256=e3b0c44298fc
designated_repro_test: null
acceptance:
- text: Given a Rust file over the size cap, when parsed, then the result is Unresolved
    with the cap named and no panic
  evidence:
  - cmd:cargo nextest run --profile ci -p gob-languages exit=0 sha256=e3b0c44298fc
- text: Given the same text, when parsed twice, then the grammar identity is identical
    and changes when the grammar crate version changes
  evidence:
  - cmd:cargo nextest run --profile ci -p gob-languages exit=0 sha256=e3b0c44298fc
threat: null
component: gob-languages
anchor: false
anchor_reason: null
land_commit: null
---
Implement crates/gob-languages per code-model.md section 3 and the audit L17. Feature-gated grammars: rust (tree-sitter-rust), markdown (tree-sitter-md), toml (tree-sitter-toml-ng or equivalent); pick tree-sitter 0.25 or 0.27 consistently and record the version choice and the ast-grep compatibility question in the done-report (audit M26). API: Language enum, detect(path) -> Option<Language>, parse(language, text) -> ParsedTree with a per-file size cap and parse timeout (both knobs) returning Unresolved markers rather than panicking, a grammar identity string (crate version + grammar hash) for cache keys, a query helper that compiles tree-sitter queries once per language (cached) and iterates captures with gob-text spans. Document how to add a language (docs comment in lib.rs and a generated docs/reference/languages page later).