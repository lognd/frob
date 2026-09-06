---
id: T-4127
title: SCOPE002 explodes on hub files (design/frob.strata, docs/modules/gates.md)
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
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
Found while working T-4110 (H3-10/SYS113): design/frob.strata (26 nodes,
each with its own frob:doc pointing at a different unrelated doc file --
roadmap.md, threat.md, cli.md, serve.md, mutate.md, host.md, several
guides/*) and docs/modules/gates.md (the master rule catalog, describing
essentially every gate module in src/frob/gates/**) are both maximal
cross-reference hubs. frob.toml promotes SCOPE002 to Severity.ERROR
([gates.severity] SCOPE002 = "error"), and SCOPE002's own closure check
(_scope002_edge_gap_violations / scope_doc_code_gaps) evaluates EVERY
symbol in a scoped FILE, not just the symbols a ticket's diff actually
touches.

Measured directly: adding design/frob.strata + docs/modules/gates.md to
T-4110's scope (needed because the ticket must remove one dead via
entry and add two new test files to two existing via lists in
design/frob.strata, plus a new rule-catalog section in gates.md) produced
141 SCOPE002 findings naming ~140 distinct unrelated files (docs/strata/
roadmap.md alone accounts for 134 symbols; the rest is nearly the entire
src/frob/gates/**.py tree via gates.md). frob check --ticket then FAILs
gate:SCOPE unconditionally for ANY ticket that touches either hub file,
regardless of how small the actual diff to it is.

This cannot be the intended behavior: a one-line addition to a shared
rule catalog or a two-line via-list edit in the self-model should not
require a ticket to also take ownership of that catalog's entire
reverse-doc-closure. Proposed fix (one of):
- SCOPE002's edge-gap check narrows to symbols the ticket's OWN diff
  hunks actually touch (or are newly introduced by), not every symbol
  the scoped FILE happens to contain -- matching SCOPE001's own
  per-touched-file (not per-scoped-file) granularity.
- Or: an explicit hub-file exemption list (config-driven, like
  [graph].exclude) for files whose reverse-doc-closure is provably
  larger than any single ticket could reasonably absorb.

Filed rather than fixed silently or worked around by disproportionately
widening T-4110's scope to ~140 unrelated files.
