---
id: T-0013
title: 'gob-symbols: symrefs, three-facet digests, imports and call graph for Rust
  and markdown'
state: queued
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0012
- T-0011
parent: T-0002
tier: ticket
sprint: null
runs_last: false
milestone: 2.0.0
flavour: null
due: null
rank: null
points: 13
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
- crates/gob-symbols/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given a Rust file, when extracted, then every public item has a symref, a
    kind and three digests, and renaming a parameter changes sig but not body
  evidence: []
- text: Given fn a calls fn b in the same crate, when affects(b) is queried, then
    a is returned
  evidence: []
- text: Given a markdown file with headings, when extracted, then each heading is
    path#slug with GitHub-style slugging
  evidence: []
threat: null
component: gob-symbols
anchor: false
anchor_reason: null
land_commit: null
---
Implement crates/gob-symbols per code-model.md sections 2 and 3 and D31. Symbol extraction for Rust (modules, fns, structs, enums, traits, impls, consts, macros, with visibility) and markdown (headings as anchors path#slug), yielding SymbolRecord { symref path::Qual.Name or path#slug, kind, span, visibility, digests { sig, body, doc } as blake3 of normalized text facets }. Imports (use trees resolved to crate-relative paths where possible) and a conservative call graph for Rust (callee names resolved within the crate, unresolved kept as names). Repository-level SymbolGraph with petgraph: nodes are symbols, edges Imports/Calls/Contains; a public-API view; affects(symref) and reach(symref, kind) queries; graph digest for repo-rule cache keys. Incremental: per-file extraction keyed by file digest through gob-cache. Parallel over files with rayon. Symref parsing and ambiguity errors per code-model.md section 2. Markdown corpus tests (plain files under tests/corpus until gob-mdtest lands) and criterion bench on this repository.