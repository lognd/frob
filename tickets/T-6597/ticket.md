---
id: T-6597
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
- mode: append
  reason: 'crunk data point: continuation-form directives invisible to the T-2114
    reader'
  actor: logan
  at: '2026-09-26'
  old_length: 1852
  new_length: 2526
- mode: append
  reason: 'crunk correction: test-side edges are read; continuation-wrapped blocks
    drop symbols'
  actor: logan
  at: '2026-09-26'
  old_length: 2526
  new_length: 3431
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


Second data point (crunk-ba, 2026-09-26): even with PRODUCTION-side
frob:tests directives the T-2114 check refused 4 symbols because the
directives were in the backslash-continuation form (`# frob:tests \`
then `# tests/...::test kind="unit"`) that `frob format --directives`
itself emits for long targets; `_frob_directive_block`'s lexical reader
takes one physical line. Same family as T-6573 (formatter emits a form a
reader rejects). Deliver, in the same change: the directive-block reader
folds continuation runs with the formatter's canonical-lines helper
before matching, and a round-trip test (format -> read) covers
frob:tests/frob:doc above a new public symbol.


Correction (crunk-ba, 2026-09-26, from two real lands): production-side
frob:tests did NOT satisfy T-2114 either (crunk T-0208 was refused with
single-line production-side directives carrying a trailing `# noqa:
E501` and a frob:waive line between them and the class), while T-0205
LANDED cleanly with TEST-side declarations written one production symbol
per physical line. So the land does read test-side edges; what breaks
both readers is a backslash-continued directive block, whose symbols
after the first physical line are silently dropped (T-6573 family). The
T-5767 frob case above may therefore have been the continuation form
too, not the cached snapshot alone. Deliver additionally: a positive
control for each of (1) a continuation-wrapped test-side block, (2) a
production-side directive with trailing `# noqa: E501`, (3) a
frob:waive line between the directive and the def; each must bind.
