---
id: T-draft-5a65f473
title: 'STORE107: `Scan` used where `Query` (key condition) would suffice, in a request
  handler (DynamoDB)'
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
- src/frob/store/_dynamodb.py
- tests/fixtures/store/store107-dynamodb-scan-vs-query/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 909
  new_length: 1047
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule id: STORE107.

Authority: AWS docs, "Best Practices for Using Scan Operations" --
research-file fetch this pass returned only nav-shell content (likely
JS-rendered); AWS docs "Query and Scan Operations in DynamoDB" also
returned minimal content. Flagged **gap, JS-rendered** in the research
file. Blocked by T-STORE-401-GAPS pending either a successful re-fetch
with a real quote, or an alternate primary source.

Call shapes:
- Python (boto3): `table.scan(...)` inside a request handler/API view
  function
- TS/JS: `docClient.send(new ScanCommand({...}))` inside a request
  handler

Detection: call-shape match on `scan(`/`ScanCommand` plus call-site
reachability from a request-handler entry point (same reachability
helper as STORE106).

Positive-control fixture:
`tests/fixtures/store/store107-dynamodb-scan-vs-query/`.

Relevance gate: boto3 DynamoDB client detected AND a web framework
detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
