---
id: T-0466
title: 'markdown frob:waive is inert: .md-embedded frob:waive produces no graph edge,
  so ref_gate (and any snapshot-edge-based gate) cannot honor a waiver on a .md file
  -- ~30 doc-anchor REF002 + .md REF001 are unwaivable; refs gate should text-scan
  .md waivers like _docblocks/DOC004 does'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_refs.py
- src/frob/gates/
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense narrative into cited ticket body per T-4691 C5 sweep
  actor: logan
  at: '2026-09-19'
  old_length: 0
  new_length: 1208
evidence:
- tests/test_refs_gate.py::TestMarkdownWaive::test_ref002_on_md_doc_suppressed_by_inline_waive
- tests/test_refs_gate.py::TestMarkdownWaive::test_ref002_on_md_doc_without_waive_still_fires
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
<!-- narrative-moved:src/frob/graph/dsl.py:521:T-0466 -->
The `frob:waive <RULE> reason="..."` markdown shape -- several gates
each independently invented their OWN tiny per-rule regex reading it
directly out of markdown TEXT, entirely outside `frob.graph`/this
module: `frob.gates._refs._md_waived_rules` (REF001/REF002, T-0466),
`frob.gates._docptr._WAIVE_DOC006_RE` (DOC006), `frob.gates.
_docblocks_refs._WAIVE_DOC004_RE` (DOC004), `frob.gates._inv.
_DOC_WAIVE_MARKER_RE` (INV003/INV004). T-1968's OWN measured evidence
(docs/modules/fuzz.md's DOC006 waivers, docs/modules/deploy.md's
INV003/INV004 waivers, `gate:DOC 0 waived`) undercounted: those two
files' waivers are almost certainly ALREADY being honored by _docptr.py/
_inv.py's own mechanisms -- `0 waived` undercounts because those
mechanisms suppress the violation BEFORE it is ever emitted (no
graph-edge WaiverRef to count), not because they do nothing. Verified by
reading each gate's own source, not re-derived from the ticket's claim
alone. `frob.gates._mutation_evidence`'s BUG002 waiver reads a ticket's
OWN body text (a different scan surface, tickets/**, not general
markdown docs) -- included here too since a ticket body IS markdown.