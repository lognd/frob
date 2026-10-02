---
id: T-0004
title: 'gob-text: spans, line index, source text'
state: done
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0003
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
worktree: /home/logan/projects/frob-v2-wt/t-0004
branch: t-0004
scope:
- crates/gob-text/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- cmd:cargo nextest run --profile ci -p gob-text exit=0 sha256=e3b0c44298fc
designated_repro_test: null
acceptance:
- text: Given any UTF-8 text and a byte offset inside it, when converted to line/column
    and back, then the original offset is returned
  evidence:
  - cmd:cargo nextest run --profile ci -p gob-text exit=0 sha256=e3b0c44298fc
- text: Given a span on a line, when rendered, then the snippet shows the line and
    a caret under the span
  evidence:
  - cmd:cargo nextest run --profile ci -p gob-text exit=0 sha256=e3b0c44298fc
threat: null
component: gob-text
anchor: false
anchor_reason: null
land_commit: null
---
Implement crates/gob-text per architecture.md section 1 and code-model.md section 2 (spans for every finding). Types: TextSize/TextRange (newtype over u32, like ruff_text_size; evaluate depending on the ruff_text_size crate from crates.io first and prefer it if its API fits, documenting the choice), LineIndex (byte offset to 1-based line/column, UTF-8 aware, UTF-16 column helper for LSP later), SourceText (Arc<str> plus LineIndex, lazily built), Span { file: FileId, range }. FileId is an interned newtype owned here. Include a snippet renderer helper that returns the line of a span with a caret (used by gob-diagnostics text output). Property tests with proptest for offset round-trips. Rustdoc on everything with examples that compile as doctests.