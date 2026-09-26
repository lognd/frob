---
id: T-draft-44f81ca8
title: frob ack cannot re-point or prune ack_log refs that no longer resolve after
  a package rename
state: queued
kind: feature
origin: agent
created: '2026-09-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
due: null
rank: null
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
- src/frob/app/ack_runner.py
- src/frob/lock/
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'DOC006 inline waivers: body names external or future-facing paths (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-26'
  old_length: 852
  new_length: 958
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by the crunk session (2026-09-26): after crunk renamed `src/apollo/...`,
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->frob.lock's ack_log still points at the old symbols. `frob graph why` reports
UnknownSymbol for each of them, but `frob ack` has no way to re-point an ack
to the renamed symbol or to prune refs that no longer resolve; `frob ack --list`
only shows the trail. Verified against dev b41443f46d: `frob ack --help` offers
facet/path/reason/list only.

Deliver (tiered safety): automatic-safe -- `frob check` reports an ack_log ref
that resolves to nothing as an advisory naming the ref; probably-safe --
`frob ack --prune` removes refs that resolve to nothing (recorded in the trail
with a reason); real decision -- `frob ack --repoint OLD NEW --reason` for a
rename. Positive control: a fixture with one dangling ref and one live ref;
prune removes exactly the dangling one.
