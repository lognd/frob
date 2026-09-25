---
id: T-draft-7fb24721
title: 'STORE301: many-to-many relationship modeled in a document store with manual
  application-side join loops'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-draft-8ae79b1b
parent: T-draft-f370cf34
tier: ticket
sprint: store-family
runs_last: false
milestone: 0.538.0
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
- src/frob/store/_strata_mismatch.py
- tests/fixtures/store/store301-document-manual-join-loop/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 1403
  new_length: 1541
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule id: STORE301 (research file section 8, cross-cutting signal #1).

Authority: MongoDB's own reference-modeling docs document the join cost
of the reference approach as the explicit tradeoff against embedding --
https://www.mongodb.com/docs/manual/tutorial/model-referenced-one-to-many-relationships-between-documents/.

Code shape: `find`/`find_one` call inside a loop over a previous query's
result set (the same N+1 shape STORE105 already flags) -- STORE301
differs from STORE105 by requiring the strata-declared paradigm for the
bound `code=` path be `document` (via T-STORE-302-ENGINE's vocabulary),
i.e. this fires only when the design ITSELF says "this is a document
store" and the code still walks it like a relational many-to-many join,
making it a declared-vs-observed mismatch rather than a bare call-shape
finding.

Detection: reuse STORE105's own N+1 detector, gate its output through
strata's declared `engine` paradigm for the bound node -- only surfaces
as STORE301 (not STORE105, which already fired independently) when the
binding's declared paradigm is `document`.

Positive-control fixture:
`tests/fixtures/store/store301-document-manual-join-loop/` (a `.strata`
fixture declaring `engine mongodb` bound to a Python file with the N+1
shape).

Relevance gate: strata `store` node declared with `engine` resolving to
`document` paradigm, AND pymongo/motor/mongoose import detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
