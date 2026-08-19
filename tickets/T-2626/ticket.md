---
id: T-2626
title: scope write path never validates individual glob syntax (semicolon-joined entries
  silently stored)
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
- src/frob/tickets/_scope.py
- src/frob/tickets/_models.py
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
Found while working T-2614 (T-2450's scope was recorded as one
semicolon-joined glob string, not two valid scope entries).

`frob ticket scope`/`new --scope`'s write path (`_validate_scope_request`
and `_validate_scope_mutation` in `src/frob/tickets/_scope.py`) never
checks that an individual scope entry is a syntactically valid glob --
only `_split_scope_entries` (`src/frob/tickets/_models.py`, T-0241)
exists, and it splits on COMMAS only. A semicolon (or any other
glob-illegal joining character) sails straight through both the CLI
write path and model construction and is stored verbatim.

The concrete failure mode this produces: a scope entry like
`'src/frob/verify/**;src/frob/app/ticket_runner/**'` is not evaluable by
`PurePath.match` as "either glob" -- it raises `ValueError: '**' can only
be an entire path component)`. Depending on which matcher call site a
given code path uses (`fnmatch.fnmatch`, which merely fails to match
anything, vs. `PurePath.match`, which raises), a malformed entry either
silently voids the ticket's write lease and evidence coverage (matches
nothing, SCOPE gate has nothing sensible to say) or crashes a caller
outright.

Two possible remedies, either or both:
1. Extend `_split_scope_entries` to also split on semicolons (matching
   the existing T-0241 comma precedent), OR
2. Add an explicit glob-validity check to `_validate_scope_request`/
   `_validate_scope_mutation` that rejects (loud error, not a silent
   store) any entry that fails a `PurePath("probe").match(entry)`
   dry-run, so a malformed pattern can never be written in the first
   place -- this is likely the more robust fix since it does not
   privilege one specific separator character over any other invalid
   glob shape.

Do not bulk-fix any other ticket's scope while implementing this --
narrow the fix's own scope to `src/frob/tickets/_scope.py`/
`src/frob/tickets/_models.py` and the CLI, not every ticket whose scope
might already be malformed.
