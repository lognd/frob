---
id: T-draft-23508d96
title: 'engine vocabulary: product->paradigm table read from the existing store engine
  attr'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-draft-62e2a780
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
- src/frob/strata/_engine_vocab.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 1523
  new_length: 1661
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
OWNER-OWNED: this leaf gives the `engine` attr its first reader and
fixes its closed vocabulary -- both are strata surface-semantics
decisions (what values `engine` may legally hold, and what a bound
`code=` path is asserting about its own store paradigm), not an
ordinary implementation leaf. Owner reviews the vocabulary table before
this leaf is dispatched.

Closed product->paradigm table (per DB-PARADIGM-ASSESSMENT.md section
3): `postgres`->relational, `mysql`->relational, `sqlite`->relational,
`mongodb`->document, `redis`->kv, `neo4j`->graph, `elasticsearch`
->search, `clickhouse`->columnar, `timescaledb`->columnar (time-series),
`influxdb`->columnar (time-series), `s3`->object, `dynamodb`->document
(AWS's own product spans document and kv depending on access pattern;
default to document, allow an explicit override). Unknown products use
an explicit `engine kv:custom`-shaped form (namespaced by paradigm,
avoids inventing product identities the registry does not know) rather
than silently guessing a paradigm.

Registers itself as `engine`'s reader in the T-STORE-301-ATTR registry
(closes ATTR002 for this key).

Acceptance criteria:
- `engine_paradigm("postgres") == Paradigm.RELATIONAL"` and equivalent
  for every table entry.
- An unrecognized bare product name with no `kv:custom`-shaped
  namespace raises/returns a typani `Result.Err`, not a silent guess.
- `engine`'s registry entry (T-STORE-301-ATTR) shows this leaf's
  qualified reader function in its `readers` tuple after this leaf
  lands.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
