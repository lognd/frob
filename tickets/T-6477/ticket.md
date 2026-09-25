---
id: T-6477
title: 'STORE303: multi-entity ACID write pattern issued against a store declared
  with no native multi-record transactions'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-6456
- T-6414
parent: T-6508
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
- tests/fixtures/store/store303-multi-entity-acid-no-txn/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-6448)'
  actor: logan
  at: '2026-09-25'
  old_length: 1661
  new_length: 1799
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule id: STORE303 (research file section 8, cross-cutting signal #3).

Authority: Redis pipelining is documented as request/response batching,
not atomicity, per Redis's own command-reference distinction between
`MULTI/EXEC` (atomic) and plain pipelining (not inherently atomic) --
https://redis.io/docs/latest/develop/using-commands/pipelining/ (page
fetched; confirms pipelining as a batching optimization distinct from
transactions). Research file flags this row **partial gap**: the
separate `MULTI`/`EXEC`/`WATCH` transaction-guarantee page was not
independently fetched this pass. Blocked by T-STORE-401-GAPS.

Code shape: multiple sequential single-item writes (`r.set`,
`table.put_item`, `collection.update_one`) across different keys/
entities within one logical operation, with no surrounding `MULTI`/
`WATCH`, `TransactWriteItems`, or DB transaction call -- this is the
same shape SQL105/STORE119's write-call-counting already establishes,
gated here by the store's declared paradigm reporting "no native
multi-record transaction primitive" (plain Redis, single-item DynamoDB
writes without `TransactWriteItems`).

Detection: reuse `_orm_rules._sql105_findings`'s write-call-counting
shape (import rather than reimplement, per the reuse note in
T-STORE-EPIC's body) with the transaction-wrapper token set extended
for `MULTI`/`WATCH`/`TransactWriteItems`.

Positive-control fixture:
`tests/fixtures/store/store303-multi-entity-acid-no-txn/`.

Relevance gate: strata `store` node declared for a paradigm with no
native multi-record transaction primitive (redis kv, or DynamoDB
document without `TransactWriteItems` in its client-kind capability
set).


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
