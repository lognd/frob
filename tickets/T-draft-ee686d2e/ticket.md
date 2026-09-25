---
id: T-draft-ee686d2e
title: 'STORE106: `$lookup` issued in a per-request hot path (MongoDB)'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-draft-6a23884f
- T-draft-46691c55
parent: T-draft-8c7707f1
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
- src/frob/store/_mongo.py
- tests/fixtures/store/store106-mongo-lookup-hotpath/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 1424
  new_length: 1562
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule id: STORE106.

Authority: general MongoDB modeling guidance frames references as
requiring app-side or `$lookup` joins as the explicit cost of
normalizing (MongoDB Manual, "Model One-to-Many Relationships with
Document References",
https://www.mongodb.com/docs/manual/tutorial/model-referenced-one-to-many-relationships-between-documents/);
the research file flags this row as a **gap** -- no dedicated
"`$lookup` in hot path" vendor warning quote was sourced. This leaf is
`blocked_by` T-STORE-401-GAPS: do not ship until that leaf closes this
citation gap with a primary source, or downgrades the rule to a
paraphrase-cited advisory tier explicitly (owner rule: every rule cites
its authority).

Call shapes:
- Python: `.aggregate([{"$lookup": ...}])` inside a per-request handler
  function (call-site context, not just call shape)
- TS/JS: `collection.aggregate([{ $lookup: ... }])` in a request handler

Detection: call-shape match on `$lookup` plus call-site reachability
from a request-handler entry point (framework-route-decorator detection,
reuse `frob.webapp.detect_frameworks`'s route markers rather than a
second router-detection pass).

Positive-control fixture:
`tests/fixtures/store/store106-mongo-lookup-hotpath/`.

Relevance gate: pymongo/motor/mongoose import AND a detected web
framework (this row needs request-handler reachability, a repo with a
mongo client but no web framework never fires it).


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
