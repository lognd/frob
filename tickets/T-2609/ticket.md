---
id: T-2609
title: land-time new-public-symbol doc/test-edge check does not offset for decorators
state: queued
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
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
## Problem

Found while working T-2585 -- the land-time new-public-symbol doc/test-edge
check (`_new_public_symbols_in_file_missing_doc_or_test_edge` /
`_frob_directive_block`, T-2114/T-2201, `src/frob/app/ticket_runner/
_land_cmd.py`) refused a land for a decorated top-level class
(`@dataclass(frozen=True)\nclass GateRunReplay:`) whose `frob:doc`/
`frob:ticket`/`frob:tests` directive block sat directly above the
DECORATOR line, even though that placement is accepted everywhere else in
this repo (the graph-based `gate:COV`/`gate:TEST` resolver, which the
`frob.lang` parser's `decorated_definition`/`_effective_node` machinery
already offsets for, had zero complaint about the same placement).

Root cause: `_public_top_level_defs` uses `ast.ClassDef.lineno`, which for
a decorated class is the `class` keyword's own line, not the decorator's.
`_frob_directive_block` then walks upward from THAT line looking for a
contiguous comment run -- for a decorated symbol, the line immediately
above `class`/`def` is the decorator itself (not a comment), so the walk
stops immediately and the directive block reads empty regardless of what
comments sit above the decorator.

Workaround used in T-2585: moved the directive comments to between the
decorator and the `class` line instead of above the decorator. Not fixed
at the root -- this land-time check's `ast`-lineno handling needs a
decorator-aware start point (e.g. `node.decorator_list[0].lineno` when
decorators are present, matching what `frob.lang`'s own graph-based parser
already does for the SAME question).

## Suggested direction

In `_public_top_level_defs` (or a caller), when `node.decorator_list` is
non-empty, walk `_frob_directive_block` from the FIRST decorator's lineno
instead of the class/def's own lineno -- same fix shape `frob.lang`'s
`_effective_node` already applies for its own directive-to-symbol binding,
just not yet ported to this separate, land-time-only text scan.
