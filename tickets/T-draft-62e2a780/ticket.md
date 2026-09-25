---
id: T-draft-62e2a780
title: 'strata attr registry: shared AttrKey table, ATTR001 unknown key, ATTR002 registered
  key with zero readers'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
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
- src/frob/strata/_attr_registry.py
- docs/modules/strata.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 1991
  new_length: 2129
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule ids: ATTR001, ATTR002 (NOT STORE-numbered -- this is shared
infrastructure any future strata attr uses, not a STORE-family rule).

Python-side only: a single `AttrKey` registry (`node_kind`, `attr_name`,
`declared_at` -- which module/leaf declared it, `readers: tuple[str,
...]` -- the qualified names of every function that reads this attr off
a parsed node). `_store_base_attrs`'s own `engine`/`durability`/`rpo`/
`immutable`/`append_only`/`managed`/`errors_total`/`panics_contained_by`
become the registry's first entries, `engine` registered with an EMPTY
reader tuple (it is a phantom key today -- T-STORE-302-ENGINE is its
first reader).

ATTR001: a `.strata` declaration attr name with no matching registry
entry (parse-time unknown key) -- this is a NEW check, distinct from
existing grammar-level parse errors; it catches an attr that parses
syntactically but was never registered, i.e. a typo or a
never-implemented keyword.

ATTR002: a registry entry whose `readers` tuple is empty -- a key that
is emitted (or declarable) but nothing in the codebase ever reads it,
the exact phantom-key state `engine` is in today. `frob check` surfaces
this as a WARN so the family does not silently accumulate more
`engine`-shaped dead attrs.

Explicitly NO grammar change: this leaf is Python-side registry plus
emit-constant cross-check only. If strata's `.strata` grammar/parser
already emits attr names as constants somewhere, this leaf reads that
constant table; it does not add new syntax.

Acceptance criteria:
- `engine` is registered with `readers=()` before T-STORE-302-ENGINE
  lands, and with a nonempty `readers` tuple after it does (verified by
  a re-run of ATTR002 in the acceptance test for that leaf, not this
  one).
- ATTR001 fires on a fixture `.strata` file carrying an unregistered
  attr name; does not fire on any currently-shipping attr name.
- ATTR002 fires on a fixture registry entry with an empty `readers`
  tuple; does not fire once a reader is registered.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
