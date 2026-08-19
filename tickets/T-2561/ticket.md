---
id: T-2561
title: Stale live lease scope drifts from an in-progress ticket's declared scope,
  undetected
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- src/frob/tickets/_leases.py
- docs/design/registry/check-coverage.yaml
- docs/modules/tickets-lifecycle.md
- tests/test_tick012_gate.py
- src/frob/gates/_tickets_gate.py
- src/frob/gates/_waive.py
evidence_scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: T-2561 adds TICK012, a new gate rule, and touches tickets_gate()'s docstring
    -- needs its registry entry and affects-doc anchor touched
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: T-2561 adds TICK012, a new gate rule, and touches tickets_gate()'s docstring
    -- needs its registry entry and affects-doc anchor touched
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_tick012_gate.py
  reason: TICK012's own test coverage lives in a new standalone test file, split out
    of tests/test_gates.py to avoid a CrossTicketLeakage collision with T-2550's current
    declared scope
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: src/frob/gates
  reason: narrowing the broad gates/ dir scope to just the two files actually touched,
    to resolve a lease collision with T-2377's own narrower scope on _exhaustive_handling.py
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_tickets_gate.py
  reason: narrowing the broad gates/ dir scope to just the two files actually touched,
    to resolve a lease collision with T-2377's own narrower scope on _exhaustive_handling.py
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_waive.py
  reason: narrowing the broad gates/ dir scope to just the two files actually touched,
    to resolve a lease collision with T-2377's own narrower scope on _exhaustive_handling.py
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_tick012_gate.py::TestTick012LeaseScopeDrift::test_stale_superset_path_fires
- tests/test_tick012_gate.py::TestTick012LeaseScopeDrift::test_lease_matching_current_scope_is_silent
- tests/test_tick012_gate.py::TestTick012LeaseScopeDrift::test_queued_ticket_with_no_lease_is_silent
- tests/test_tick012_gate.py::TestTick012LeaseScopeDrift::test_dir_scope_still_covers_its_own_lease_paths
designated_repro_test: tests/test_tick012_gate.py::TestTick012LeaseScopeDrift::test_stale_superset_path_fires
designated_repro_changes:
- old_value: tests/test_gates.py::TestTick012LeaseScopeDrift::test_stale_superset_path_fires
  new_value: tests/test_tick012_gate.py::TestTick012LeaseScopeDrift::test_stale_superset_path_fires
  reason: TICK012's tests moved to a new standalone file to avoid a scope collision
    with T-2550; re-verified FAILED_AT_PARENT against the new file's own pre-implementation
    commit
  actor: logan
  at: '2026-08-18'
evidence_changes:
- old_node: tests/test_gates.py::TestTick012LeaseScopeDrift::test_dir_scope_still_covers_its_own_lease_paths
  new_node: tests/test_tick012_gate.py::TestTick012LeaseScopeDrift::test_dir_scope_still_covers_its_own_lease_paths
  reason: moved TICK012's coverage to a standalone file to avoid a CrossTicketLeakage
    collision with T-2550's declared scope; re-pointing evidence/repro node ids at
    the new location
  actor: logan
  at: '2026-08-18'
- old_node: tests/test_gates.py::TestTick012LeaseScopeDrift::test_stale_superset_path_fires
  new_node: tests/test_tick012_gate.py::TestTick012LeaseScopeDrift::test_stale_superset_path_fires
  reason: moved to standalone file
  actor: logan
  at: '2026-08-18'
- old_node: tests/test_gates.py::TestTick012LeaseScopeDrift::test_lease_matching_current_scope_is_silent
  new_node: tests/test_tick012_gate.py::TestTick012LeaseScopeDrift::test_lease_matching_current_scope_is_silent
  reason: moved to standalone file
  actor: logan
  at: '2026-08-18'
- old_node: tests/test_gates.py::TestTick012LeaseScopeDrift::test_queued_ticket_with_no_lease_is_silent
  new_node: tests/test_tick012_gate.py::TestTick012LeaseScopeDrift::test_queued_ticket_with_no_lease_is_silent
  reason: moved to standalone file
  actor: logan
  at: '2026-08-18'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 5d9dcb17a1db1c45520fe154efe920f8733dc4a4
milestone: null
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