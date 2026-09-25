---
id: T-draft-20bea778
title: 'STORE105: `find`/`find_one` inside a loop over a prior query''s result (N+1,
  MongoDB)'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-draft-6a23884f
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
- tests/fixtures/store/store105-mongo-n-plus-1/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 1263
  new_length: 1401
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule id: STORE105.

Authority: MongoDB Manual, "Model One-to-Many Relationships with
Document References": "If the number of books per publisher is
unbounded, this data model creates mutable, growing arrays" --
https://www.mongodb.com/docs/manual/tutorial/model-referenced-one-to-many-relationships-between-documents/
(general reference-modeling join-cost framing this row's own authority
note in the research file draws the N+1 tradeoff from).

Call shapes:
- Python (pymongo/motor): `for parent in collection.find(...): child =
  other_collection.find_one({"parent_id": parent["_id"]})` (a DB call
  inside a loop over a prior query's result set)
- TS/JS: `for (const p of parents) { const c = await
  Other.findOne({parentId: p._id}) }`, mongoose `.populate()` in a loop

Detection: this is the SAME shape SQL101 already detects for a different
receiver kind -- import `frob.sql._orm_rules._for_loop_targets` and
`_attribute_accesses_on`/loop-body-call-scan helpers rather than
reimplementing the loop-body walk; swap SQL101's ORM-eager-load-name
check for a "no batched `$lookup`/aggregation call in the same function"
check.

Positive-control fixture:
`tests/fixtures/store/store105-mongo-n-plus-1/`.

Relevance gate: pymongo/motor/mongoose import detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
