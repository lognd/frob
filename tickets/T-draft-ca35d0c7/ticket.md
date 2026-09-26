---
id: T-draft-ca35d0c7
title: land T-2114/T-5299 new-public-symbol check reads the cached graph snapshot,
  which predates the ticket own test-side frob:tests declaration, and refuses a correctly
  bound symbol
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
due: null
rank: null
points: null
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
- src/frob/gates/_land_parity.py
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: DOC006 inline waivers (T-draft-7ee140de)
  actor: logan
  at: '2026-09-26'
  old_length: 1640
  new_length: 1852
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-26 landing T-5767 twice: "refused -- src/frob/webapp/
_layout_structure.py:155 new public symbol 'layout_findings' has no
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->frob:tests edge (T-2114)" although tests/unit/test_layout_gate.py (a file
the same ticket adds) carries the test-side declaration
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->`# frob:tests src/frob/webapp/_layout_structure.py::layout_findings`
directly above test_unreviewed_entry_raises_layout001, which is also bound
evidence. Verified on dev e98e686cbc: `_symbol_has_test_side_edge`
(src/frob/gates/_land_parity.py, T-5299) consults the snapshot from
`_land_parity_graph_snapshot`, which "prefers the already-cached snapshot
(load_graph)"; at land that cache predates the merge (or is absent, in
which case the helper returns False, contradicting its own docstring's
"treated as covered"), so a test-side-only binding introduced by the
ticket itself is invisible and the land is refused. The T-4710 direction
(declare on the test side; TEST010 deletes the production copy) therefore
cannot pass this check on the first land of a new public symbol.
Workaround used: moved the declaration to the legacy production side.

Deliver: the check derives test-side edges for the touched set directly
(`parse_directives` over the touched test files, same orientation logic
as `_reorient_test_edge`) and unions them with the cached snapshot; the
None-snapshot branch follows the docstring (covered, logged) or the
docstring is corrected, never a silent refusal. Positive control: a
fixture where a ticket adds a public symbol and a test-side-only
declaration in a new test file with no graph cache; the check passes,
and an unbound symbol still refuses.
