---
id: T-3945
title: normalize_evidence_separator mangles real kotlin node ids (dot-form classname.method)
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
- src/frob/tickets/__init__.py
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
Found while working T-3937 (evidence binding real-collector fixtures).

normalize_evidence_separator (src/frob/tickets/__init__.py) rewrites the
FIRST dot found after a node id's '::' prefix into another '::' -- this is
correct for python's path::Class.method convention, but every real kotlin
node id collect_kotlin_tests produces (_collect_kotlin.py::_kotlin_node_id)
is dotted classname.method (path::classname.method, or dotted
package.Class.method in the fallback shape), and gets silently mangled by
this rewrite before it ever reaches matches_collected -- so a real,
correctly-collected kotlin id taken verbatim from the collection cache can
never bind via 'frob ticket evidence', identically to F-172's
UnknownEvidence symptom but caused by a different function.

Repro: collect_kotlin_tests produces 'app::com.example.FooTest.doesThing'.
normalize_evidence_separator turns that into
'app::com::example.FooTest.doesThing' (rewrites only the first dot after
'::'), which does not exact-match the collected id, so add_evidence
rejects it as UnknownEvidence even though the test genuinely exists and
was genuinely collected.

Fix should make normalize_evidence_separator either a no-op for a kotlin-
shaped remainder (multiple dots) or otherwise not applicable outside
python's specific Class.method (single dot) shape -- needs care not to
regress the existing T-0293/T-0282/T-0217 python dot-form fix this
function exists for.