---
id: T-2237
title: 'T-2226 residue: 2 DOC011 dangling T-draft-* prose citations, mappings resolved
  via git archaeology, blocked by live leases on the target docs'
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/design/gate-semantics-classification.md
- docs/guides/coordinator-scripts.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2226 residue. Two DOC011 findings cite a `T-draft-*` id that no longer
resolves:

    docs/design/gate-semantics-classification.md:123 -> 'T-draft-385de2c7'
    docs/guides/coordinator-scripts.md:467           -> 'T-draft-354a6b64'

Both mappings are RESOLVED via git archaeology (no live promote-mapping
artifact exists anywhere in this repo -- checked; the mapping had to be
reconstructed from commit history):

- `T-draft-385de2c7` -> `T-2188`. Confirmed via commit f90723df4
  ("chore(tickets): T-2188 id field sync post-promote"), which HAND-EDITS
  `tickets/T-2188/ticket.md`'s `id:` field from `T-draft-385de2c7` to
  `T-2188` directly -- bypassing `renumber_one`'s directory-move +
  cross-file prose rewrite entirely (the same malformed-promote shape
  T-2199 exists to fix going forward, but this predates it and touched no
  code path T-2199 covers). Title match confirmed:
  "callgraph.py's build_call_graph/build_reference_graph/
  build_ordered_call_graph resolve cross-file private candidates by bare
  short name, unverified against imports" == the doc prose's own
  description of "the callgraph substrate itself".

- `T-draft-354a6b64` -> `T-2172`. Confirmed via commit f2ec5e458 ("fix
  (tickets): land T-2172 scripts/fleet_status.py::main crosses
  ARCH001/ARCH103 after T-2129/T-2133's land (230-line growth)"), whose
  diff modifies `docs/guides/coordinator-scripts.md` (46 lines) IN THE
  SAME COMMIT that finalized the draft to T-2172 -- the draft-id prose
  was added to the doc in that same commit, before `finalize_draft_
  for_land`'s renumber scan ran over the diff, so the scan never saw it
  and never rewrote it. A land-ordering gap, not a hand-edit.

## Why not fixed directly under T-2226

Both target files are under a LIVE cross-ticket scope lease at the time
T-2226 ran (T-1662 on gate-semantics-classification.md, T-2222 on
coordinator-scripts.md) -- `frob ticket scope T-2226 --add` refused both
with `ScopeLeaseConflict`. T-2226's own instructions are explicit not to
force a lease conflict.

## Acceptance criteria

1. `docs/design/gate-semantics-classification.md:123` reads `T-2188`
   instead of `T-draft-385de2c7`.
2. `docs/guides/coordinator-scripts.md:467` reads `T-2172` instead of
   `T-draft-354a6b64`.
3. Both substitutions are applied via a real edit (not a blind
   regex/sed across the whole doc -- these are the ONE known-resolved
   occurrence each; verify no OTHER stale draft-id citation exists
   nearby before editing).
