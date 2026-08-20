---
id: T-2683
title: Consumer-side self-disclosure when an OPTIONAL adapter capability gap silently
  degrades output
state: queued
kind: feature
origin: human
created: '2026-08-19'
priority: medium
blocked_by:
- T-1599
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/callgraph.py
- src/frob/cycle/__init__.py
- docs/modules/lang.md
- docs/modules/graph.md
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
docs/modules/lang.md's "Optional-capability degradation" section
(T-1599, deliverable 4) documents that a KNOWN_GAP on an OPTIONAL
capability (call_graph / import_graph / test_discovery) is loud at the
REGISTRY layer (LANG001/LANG003, frob check's own output) but silent at
each DOWNSTREAM CONSUMER's own output today: frob.graph.callgraph,
frob.cycle, and evidence binding all just quietly produce fewer/no
edges for an affected language, with nothing in THEIR OWN output
(DEAD001 findings, cycle001 findings, evidence-gate results) saying
"this analysis is incomplete for language X because of an OPTIONAL
capability gap."

No registered language has a live call_graph/import_graph KNOWN_GAP
today (both fully IMPLEMENTED across every registered language, see
that section's own note), so this is currently a latent gap in the
contract, not an active one -- filed as real, unbuilt follow-up scope
per the coordinator's fail-loudly doctrine (T-2391) rather than left
undocumented.

Scope: make each consumer (frob.graph.callgraph's DEAD001/closure
consumers, frob.cycle, evidence-binding gates) check the relevant
capability's registry cell for languages present in ITS OWN input set
and self-disclose (a WARN-severity note, not necessarily a build
failure) when it silently degraded for at least one file because of an
OPTIONAL KNOWN_GAP cell -- mirroring the LANG003 "present in this
repo's tree" pattern, just at the consumer layer instead of the
registry layer.
