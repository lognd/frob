---
id: T-3332
title: ROOT001's frob:external-reader remedy fires DSL001 (diax F-007)
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_root_asset_dirs.py
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
Found in ../diax FROBLEMS.md (F-007), noted while working T-3277 (do not
have bandwidth to fully verify/fix there -- filing per T-3277's own
instructions to file rather than fold in).

ROOT001's own suggested remedy is a `<!-- frob:external-reader dir="name"
reason="..." -->` markdown comment (see src/frob/gates/_root_asset_dirs.py
check (c)). Per the diax report, actually adding one of these to a
tracked markdown file fires DSL001 instead, because the `frob:external-
reader` verb is not in DSL001's markdown-comment-directive allowlist,
while `_root_asset_dirs.py` itself reads the directive with a bare regex
independent of that allowlist. Net effect: ROOT001's documented escape
hatch is unusable without triggering a different gate.

NOT independently re-verified against DSL001's allowlist source in this
ticket -- filing so someone can confirm against the DSL001 verb list and
`_root_asset_dirs.py`'s directive regex directly, then either add
`frob:external-reader` to DSL001's allowlist or correct ROOT001's own
suggested-fix message if the directive is meant to be used a different
way.

Relevant to T-3277: this blocks the "gate bug" fix path for ROOT001
flagging .github/ and invariants/ in every python-family scaffold (both
directories the scaffold itself creates, both with a legitimate external
reader -- GitHub Actions and future frob:invariant tooling respectively).
T-3277 leaves those two as WARN-only (non-blocking) findings rather than
using the broken external-reader directive.
