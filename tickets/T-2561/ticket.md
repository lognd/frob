---
id: T-2561
title: Stale live lease scope drifts from an in-progress ticket's declared scope,
  undetected
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_leases.py
- src/frob/gates
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
`_effective_leakage_scope` (T-2547) now voids any ticket's attribution
claim once its DECLARED scope is empty, closing the misattribution T-2547
was filed for. But that fix treats the symptom at the read site, not the
write-time drift that produces it: an IN_PROGRESS ticket can hold a live
cross-worktree lease (`.git/frob-leases/<id>.json`) whose recorded scope
has gone stale relative to the ticket's current declared scope -- most
sharply when the declared scope has been narrowed all the way to empty
by some path other than a fully lease-syncing `mutate_scope` call, but
the lease is never refreshed to match.

Confirmed live in this repo while working T-2547 (2026-08-18): T-2374 is
`state: in-progress` with `scope=[]` on its ticket record, yet its lease
file (`.git/frob-leases/T-2374.json`) still lists ~27 paths accumulated
earlier in its own history, including an unrelated sibling ticket's own
ledger shard (`tickets/T-2524/ticket.md`). Nothing currently detects
this drift: no gate flags an IN_PROGRESS ticket whose live lease scope
diverges from (in particular, is broader than) its own current declared
scope. `_effective_leakage_scope`'s new empty-scope short-circuit
neutralizes THIS ticket's specific consequence for CrossTicketLeakage,
but the underlying lease-vs-declared-scope drift is still silently live
and could still cause other confusion (a `frob ticket doable` collision
check, a `--add` conflict refusal naming paths the ticket no longer
actually wants, etc. -- any OTHER consumer of `read_all_leases` that
does not happen to share T-2547's empty-scope carve-out).

Proposed direction: a gate (or `frob ticket start`/`scope`-time check)
that compares an IN_PROGRESS ticket's live lease scope against its
current declared scope and flags/logs when the lease is a strict
superset the ticket no longer claims -- surfacing the drift instead of
requiring another empty-declared-scope incident to notice it. Whether
this belongs as a new gate code, a <!-- frob:waive DOC006 reason="illustrative hypothetical name for a not-yet-built diagnostic subcommand, not a claim that `frob ticket doctor` currently exists" -->`frob ticket doctor`-style diagnostic,
or a `mutate_scope`-adjacent write-time guard is an open design question
for whoever picks this up.

## Resolution (this pass)

Implemented as a read-time gate, TICK012
(`frob.gates._tickets_gate._tick012_lease_scope_drift`), not a
`mutate_scope`-adjacent write-time guard -- both `mutate_scope`
(`src/frob/tickets/_scope.py`) and every ticket_runner write path that
could call it sit outside this ticket's declared scope
(`src/frob/tickets/_leases.py`, `src/frob/gates`), and a write-time guard
placed there would have been an undeclared scope expansion. TICK012
compares each IN_PROGRESS ticket's live lease scope
(`read_all_leases`) against its CURRENT declared scope via
`scope_matches` (T-0241's shared directory/glob-aware matcher, not a
literal string/set diff) and emits one WARN per drifted lease, naming
the stale paths -- covering every `read_all_leases` consumer generally,
not only the CrossTicketLeakage/empty-scope case T-2547 already closed.
