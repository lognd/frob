---
id: T-draft-cfca7c7e
title: 'STORE207: single-table DynamoDB design with no documented access-pattern key
  schema'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-draft-6a23884f
- T-draft-46691c55
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
- src/frob/store/_dynamodb.py
- tests/fixtures/store/store207-dynamodb-single-table-no-schema/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 1000
  new_length: 1138
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule id: STORE207.

Authority: AWS docs, "Best Practices for Designing and Architecting with
DynamoDB" --
https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-general-nosql-design.html
(fetched; confirms the page covers this topic but did not yield a short
pull-quote distinct from the page title/nav this pass). Research file
flags this **partial gap**. Blocked by T-STORE-401-GAPS.

Call shapes: `table.put_item(Item={...})` with heterogeneous `Item`
shapes and a generic `PK`/`SK` naming convention but no access-pattern
doc/tests; TS/JS: `docClient.send(new PutCommand({...}))` same shape.

Repo fact needed: presence (or absence) of a repo-tracked access-pattern
doc (a `docs/`-tree file referencing the table's `PK`/`SK` design) --
this is the "documented" half of the check; heterogeneous `Item` shape
detection is the call-shape half.

Positive-control fixture:
`tests/fixtures/store/store207-dynamodb-single-table-no-schema/`.

Relevance gate: boto3 DynamoDB client detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
