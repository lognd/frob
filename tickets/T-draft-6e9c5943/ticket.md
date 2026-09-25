---
id: T-draft-6e9c5943
title: 'STORE208: collection query missing index coverage (`find({})`/leading-wildcard
  `$regex`, MongoDB)'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-draft-6a23884f
parent: T-draft-8980afab
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
- tests/fixtures/store/store208-mongo-scan-no-index/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 918
  new_length: 1056
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule id: STORE208.

Authority: MongoDB Manual, "Indexes": "Without indexes, MongoDB must
scan every document in a collection to return query results. If an
appropriate index exists for a query, MongoDB uses the index to limit
the number of documents it must scan" --
https://www.mongodb.com/docs/manual/indexes/.

Call shapes: pymongo `collection.find({})` with no filter/limit on a
collection referenced elsewhere as large; `collection.find({"field":
{"$regex": f"^.*{q}"}})`; TS/JS: `Model.find({})`,
`collection.find({field: {$regex: q}})` with leading wildcard.

Repo fact needed: index list from schema/migration files to confirm
absence of a matching index (the call shape itself is static: yes per
the research row, this repo fact just confirms it is not already
covered).

Positive-control fixture:
`tests/fixtures/store/store208-mongo-scan-no-index/`.

Relevance gate: pymongo/motor/mongoose import detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
