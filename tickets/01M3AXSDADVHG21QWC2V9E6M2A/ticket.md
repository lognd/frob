+++
id = "01M3AXSDADVHG21QWC2V9E6M2A"
title = "STORE303: multi-entity ACID write pattern issued against a store declared with no native multi-record transactions"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSDBCZ0WN62JE8P0BQRA2"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:25Z"
aliases = ["T-6477"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_strata_mismatch.py", "tests/fixtures/store/store303-multi-entity-acid-no-txn/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD8EJE4SFMVFJJF41NMA"

[[links]]
kind = "blocked-by"
target = "01M3AXSD9RZ5GY6YQ2MDV558BD"
+++

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
