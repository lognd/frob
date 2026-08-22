---
id: T-2626
title: scope write path never validates individual glob syntax (semicolon-joined entries
  silently stored)
state: done
kind: bug
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
- src/frob/tickets/_scope.py
- src/frob/tickets/_models.py
- tests/test_tickets.py
evidence_scope:
- tests/test_tickets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets.py
  reason: 'SCOPE001: T-2626''s repro/positive-control tests live here'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/test_tickets.py
  reason: 'SCOPE001: T-2626''s repro/positive-control tests live here'
  actor: logan
  at: '2026-08-19'
evidence:
- tests/test_tickets.py::TestScopeGlobValidation::test_semicolon_joined_entry_is_invalid
- tests/test_tickets.py::TestScopeGlobValidation::test_absolute_pattern_is_invalid
- tests/test_tickets.py::TestScopeGlobValidation::test_every_existing_valid_form_still_passes
- tests/test_tickets.py::TestScopeGlobValidation::test_new_ticket_refuses_a_semicolon_joined_scope
- tests/test_tickets.py::TestScopeGlobValidation::test_ticket_itself_still_loads_a_legacy_malformed_scope
- tests/test_tickets.py::TestScopeGlobValidation::test_mutate_scope_refuses_a_semicolon_joined_add
- tests/test_tickets.py::TestScopeGlobValidation::test_mutate_scope_still_accepts_every_valid_form
designated_repro_test: tests/test_tickets.py::TestScopeGlobValidation::test_mutate_scope_refuses_a_semicolon_joined_add
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 8bd384ab4abaa3b5f3f9505820a7d9ba21e3ac8a
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