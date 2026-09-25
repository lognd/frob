---
id: T-6508
title: STORE3xx declared-vs-observed via strata
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-6430
tier: story
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-6448)'
  actor: logan
  at: '2026-09-25'
  old_length: 1064
  new_length: 1202
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The paradigm-level mismatches (many-to-many in a document store, ACID
writes against a non-transactional store, graph-shaped traversal
reimplemented relationally, a search index treated as source of truth)
are only decidable once the design states WHICH store a code path talks
to and what KIND it is -- exactly the `engine` slot on strata's `store`
node plus its `code=` binding (`_infra.py::_store_base_attrs` already
emits `engine=<ident>`, currently read by nothing). Four leaves, strictly
ordered: (a) a shared attr registry so `engine` gets a reader at all and
future attrs stop being phantom keys; (b) a closed product->paradigm
vocabulary read off that attr, OWNER-OWNED because it touches strata
surface semantics; (c) new vet capability kinds per store client library
so SYS100/SYS101 already refuse an undeclared store client in a bound
file, the same enforcement SYS100/SYS101 already give every other
capability kind; (d) the five STORE30x rules themselves, each comparing
the declared paradigm against the observed access pattern in the bound
files.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
