---
id: T-draft-e3e69803
title: 'STORE117: `ListObjectsV2` with no `Prefix`, or called in a loop, to "find"
  an object (S3)'
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
- tests/fixtures/store/store117-s3-list-objects-scan/**
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
Rule id: STORE117.

Authority: AWS docs, "Listing object keys programmatically" confirms
`ListObjects`/`ls` as the API surface for enumeration --
https://docs.aws.amazon.com/AmazonS3/latest/userguide/ListingKeysUsingAPIs.html.
Research file flags this **partial gap**: a standalone "don't use
listing as a query mechanism" caveat was not isolated verbatim this
pass. Blocked by T-STORE-401-GAPS.

Call shapes:
- Python (boto3): `boto3.client('s3').list_objects_v2(Bucket=b)` called
  repeatedly/in a loop with `ContinuationToken` to search for a specific
  object by attribute
- TS/JS: `s3.send(new ListObjectsV2Command({ Bucket: b }))` in a loop
  searching by attribute
- Go: `s3.ListObjectsV2` in a loop

Detection: call-shape match on `list_objects*`/`ListObjectsV2` whose
result is filtered/searched in app code rather than a direct
`get_object`/`head_object` by a known key.

Positive-control fixture:
`tests/fixtures/store/store117-s3-list-objects-scan/`.

Relevance gate: boto3 (or equivalent) S3 client import detected.
