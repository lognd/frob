---
id: T-6578
title: 'frob format --directives wraps frob:secret-fake across a backslash continuation
  but SEC004 only reads a single physical line: formatter and parser disagree'
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
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
- src/frob/gates/_fmt_directives.py
- src/frob/gates/_secrets.py
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
Reported by the crunk session (2026-09-26): `frob format --directives`
line-wrapped a long `frob:secret-fake reason="..."` marker across the
frob backslash continuation, after which SEC004 no longer recognised the
marker (its parser reads a single physical line: see the comment at
src/frob/gates/_secrets.py near "single-physical-line"). Collapsing it
back to one line then tripped E501. Verified on dev b41443f46d: the
directive formatter treats every `frob:` directive as wrappable while
the secrets gate's marker scan is line-local.

Deliver one of: (a) SEC004 folds continuation runs the same way
_fmt_directives' canonical-lines helper does before scanning (preferred:
one continuation syntax, owned by frob, read by every consumer); or (b)
the formatter never wraps `secret-fake` and the gate documents the
single-line rule and exempts it from E501 the way other directive lines
are. Positive control: a wrapped marker fixture is recognised by SEC004
and a bare token without a marker still fires.
