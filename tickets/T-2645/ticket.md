---
id: T-2645
title: unlanded-branch directive parsing uses a temp-file round trip per candidate
state: in-progress
kind: feature
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_unlanded.py
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
`_directive_ids_via_real_parser` (`src/frob/tickets/_unlanded.py:508`)
writes candidate text to a `tempfile.NamedTemporaryFile` purely so
`parse_file` has a path to open, then runs a full tree-sitter parse per
directive candidate. That is a syscall-heavy round trip (open/write/
flush/close/unlink) for every single candidate, on top of the parse
itself.

Filed separately per T-2629's own instruction not to fold this in: T-2629
took the minimum fix (stop `doable`'s render path from triggering the
scan inline on a cache miss). The scan itself, wherever it does run
(`frob ticket reconcile`, a warm cache refresh), still pays this temp-file
tax per candidate.

If `frob.lang`'s parser can accept in-memory content directly (a
`parse_text`/`parse_bytes` entrypoint, or `parse_file` accepting a
`Path | str` content buffer), swap to that and drop the temp-file round
trip. If the parser genuinely cannot parse without a real path on disk,
that constraint is worth documenting explicitly rather than
re-discovering by reading the code again.

Scope note: touches `frob.tickets._unlanded` and, if a new parser
entrypoint is needed, `frob.lang`'s own module -- not `_query.py`.
