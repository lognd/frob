---
id: T-draft-71109a6f
title: 'STORE118: `HeadObject`/`GetObject` in a loop over a candidate key list to
  filter by metadata (S3)'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
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
- src/frob/store/_object.py
- tests/fixtures/store/store118-s3-head-object-loop/**
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
Rule id: STORE118.

Authority: same listing-API page family as STORE117; S3 has no
query-by-metadata API, so any "query" necessarily becomes N
`HeadObject` calls -- structural absence of the capability is the
signal. Research file flags this row **gap** (no dedicated quote
sourced this pass). Blocked by T-STORE-401-GAPS.

Call shapes:
- Python: `for key in keys: s3.head_object(Bucket=b, Key=key)` to
  filter by metadata before use
- TS/JS: loop of `HeadObjectCommand` calls

Detection: S3 metadata call inside a loop over a candidate key list --
same N+1 family as STORE105/STORE116, reuse the shared loop-body
helpers.

Positive-control fixture:
`tests/fixtures/store/store118-s3-head-object-loop/`.

Relevance gate: boto3 (or equivalent) S3 client import detected.
