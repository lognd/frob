---
id: T-5081
title: 'Strata module system: imports, export surfaces, two-sided contracts, per-module
  elaboration and link; monolith split module by module (owner decisions D-M1..D-M8)'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
parent: T-4662
tier: story
sprint: null
runs_last: false
milestone: 0.536.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: 'tier=story rollup: all file work lives in its leaves'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.536.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
body_changes:
- mode: set
  reason: 'DOC006: the rejected sys-split tool must not read as a cli invocation pointer
    (it does not exist by owner decision D-M6)'
  actor: logan
  at: '2026-09-19'
  old_length: 2839
  new_length: 2839
- mode: append
  reason: record the D-M9 module hierarchy order in the story body
  actor: logan
  at: '2026-09-19'
  old_length: 2839
  new_length: 3718
- mode: set
  reason: repair the DOC006 rewrite that left 'NO a sys-split tool tool' and restore
    the hierarchy section in one coherent body
  actor: logan
  at: '2026-09-19'
  old_length: 3718
  new_length: 3734
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Owner decisions 2026-09-19 18:30 (binding). Source: scratchpad STRATA-MODULES.md
(proposal with sourced facts: no import/export construct exists today; names are
global; multi-file designs are merged into one flat bag in
src/frob/strata/_multifile.py; the 11-module partition has 109 of 117 flows
crossing a boundary and 16 bidirectional module pairs).

DECIDED: Option C (imports + private-by-default export surface + two-sided
cross-module flow contracts via `accepts`), delivered by Option D (per-module
elaboration plus an explicit link step), with Option A (dotted namespaces)
folded in.

D-M1 privacy: YES. Private-by-default export surfaces; unexported names are
unnameable outside the module.
D-M2 import cycles: HARD compile error with the full path printed
(a -> b -> c -> a). Shipped only AFTER the 16 existing bidirectional pairs are
each decided individually -- never bulk-waived.
D-M3 cross-module flow: BOTH sides declare. Importer declares the `flow`,
exporter declares `accepts <flow> from <module>` on the exported node. One side
alone is a checker error (deny-by-default, charter law 2).
D-M4 kernel: exactly ONE new attribute, `module` on Node. Nothing else. No
Module primitive, no module-level flows, no module trust levels.
D-M5 partition: KEEP the 11 modules of the proposal (platform, tickets, graph,
gates, strata, vet, deploy, natives, serve, app, test).
D-M6 OVERRIDDEN: there will be no sys-split tool; the owner rejected one. The split of
design/frob.strata is a one-time reviewed rewrite done by agents, module by
module, with the 111 duplicate declaration lines (SF-10) removed in the
process. The migration must NOT leave a half-split state on dev: each module
lands as a coherent file with its contracts, the monolith shrinking by exactly
that module on each land, checker green at every step.
D-M7 per-module leases and per-module via-ratchet locks: LAST, after isolation
is real. Grants and the ratchet lock stay whole-file until that leaf.
D-M8 OVERRIDDEN AND STRENGTHENED: the 33 boilerplate CWE assumes (SF-08, one
template per node per CWE with identical owner and date) are NOT carried over.
An assume must be module-owned and SPECIFIC: its reason text names the concrete
mechanism or evidence gap for THAT module. A structural gate refuses templated
assumes -- two assumes whose text is identical after substituting the
node/module name are a finding (token-level comparison, not a keyword
heuristic), as are assumes sharing one expiry date across more than N modules.
That gate is a leaf of this story and MUST be red on today's design/frob.strata
as its positive control.

Refused by construction (section 5 of the proposal): wildcard imports, implicit
re-export, global name fallback, string-path cross-module references,
module-level flows, auto-generated exports, `part of` fragments as the
modularity story.

## Module hierarchy (D-M9, owner 2026-09-19 19:30)

Modules declare their position explicitly. Import is UPWARD ONLY (importing a
module below you is a compile error naming both modules), so import cycles are
impossible by construction. Flows are declared by the LOWER module in either
direction, because only the lower module can name both ends; the upper module
declares `accepts f from <lower-module>` by reference, with no import. An
`accepts` naming a module above you is an error.

Top-down order of the 11-module partition:
  1. platform   (top: imports nothing; shared vocabulary)
  2. tickets
  3. graph
  4. strata
  5. vet
  6. gates
  7. natives
  8. deploy
  9. serve
  10. app       (bottom)
  11. test      (bottom)

The 16 bidirectional pairs are NOT waivers: each migration leaf decides which of
the two modules is lower and moves the flow declarations there.
