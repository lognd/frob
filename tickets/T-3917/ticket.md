---
id: T-3917
title: tree-sitter-language-pack's >=0.13 lower bound has crossed a major (now 1.16.1
  upstream), unbounded upper
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- pyproject.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-3903 (a sibling defect reported by Series FE, folded in here per T-3903's instructions since it is cheap to file).

pyproject.toml:30 pins tree-sitter-language-pack>=0.13 with no upper bound. Upstream has since released 1.16.1 -- a major version crossed while the repo's bound stayed open, so a fresh resolve can silently pick up a 1.x release whose API/grammar set frob has never been tested against. This is a DIFFERENT defect class from T-3903 (VERSION001 governs frob-core/strata-core sibling-crate lockstep pins, not third-party dependency bounds) so it is not folded into that gate; filing separately.

WHAT TO DO: audit tree-sitter-language-pack 0.13 -> 1.16.1's changelog for breaking changes relevant to frob's usage (grammar loading API, language identifiers), then either bound it (e.g. >=0.13,<2 or pin to a tested 1.x) or upgrade deliberately and widen the bound with a comment recording why, matching the style of the existing T-3857 comment on the mcp bound in this same file.

Cross-ref: T-3903 (where this was folded in as a reported finding, not fixed).