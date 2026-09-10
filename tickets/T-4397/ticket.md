---
id: T-4397
title: 'frob check blowup: load_queue reparsed O(leases) times in TICK010 holder-dead
  pass'
state: done
kind: bug
origin: human
created: '2026-09-10'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_archive.py
- tests/gates_suite/test_run.py
- src/frob/gates/_tickets_gate.py
scope_breadth_ack: true
scope_breadth_ack_reason: 'src/frob/gates/_tickets_gate.py is a bundled multi-rule
  ledger-hygiene module (TICK001-014) whose own module-level LARGE001 waiver already
  documents this, same as T-4319''s identical scope-ack on this file: the fix lives
  in _tick010_holder_dead_pass, but touching the file at all pulls in every OTHER
  pre-existing rule''s frob:doc/frob:tests targets via SCOPE002''s closure check --
  this file''s own chronic breadth, not new breadth from this change'
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: load_queue_run_scope() must be entered around run_gates' call tree (_load_graph_queue_lock
    and tickets_gate share it) so the O(leases) reload the ticket fixes is actually
    avoided end to end
  actor: logan
  at: '2026-09-10'
- op: remove
  glob: src/frob/gates/__init__.py
  reason: 'reverting: wrapping gates/__init__.py pulls in 303 unrelated scope-closure
    warnings on that huge shared file; the fix belongs entirely inside _tickets_gate.py
    instead, entering load_queue_run_scope() around the per-lease loop that is the
    actual O(leases) hot path'
  actor: logan
  at: '2026-09-10'
- op: add
  glob: src/frob/gates/_tickets_gate.py
  reason: 'the actual O(leases) hot path: _tick010_holder_dead_pass loops leases and
    each iteration''s lease_staleness_reason call reloads the whole ledger -- entering
    load_queue_run_scope() around that loop is the fix, contained entirely inside
    this file per the coordination note (another agent holds _leases.py)'
  actor: logan
  at: '2026-09-10'
evidence:
- tests/gates_suite/test_run.py::TestLoadQueueMemoization::test_load_queue_is_memoized_across_the_whole_tickets_gate_call
- tests/gates_suite/test_run.py::TestLoadQueueMemoization::test_load_queue_reloads_outside_a_run_scope
- tests/gates_suite/test_run.py::TestLoadQueueMemoization::test_load_queue_run_scope_caches_within_the_with_block
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured: frob check --only tickets does not finish within 540s via the CLI while the tickets gate called in-process with a pre-loaded queue takes ~2.8s. cProfile of _load_graph_queue_lock shows ONE load_queue(root) call already costs ~10.2s (parsing ~4200 active+archive ticket YAML frontmatters). _tick010_holder_dead_pass (T-4319, src/frob/gates/_tickets_gate.py) calls frob.tickets._leases.lease_staleness_reason once per lease file in .git/frob-leases/, which internally calls _ticket_ledger_staleness_shape -> load_queue(root) AGAIN per lease -- a full ~10s ledger re-parse per lease on top of the one legitimate load run_gates already did, so check time grows O(leases x ledger-size) rather than O(ledger-size). Fix: decorate frob.tickets._archive.load_queue with @memoize_per_run (frob.check._memo, the existing run-scoped memoization pattern already used for build_graph/analyze_project) so every call after the first within one frob check invocation is a cache hit; scoped to run_memo_scope() so the other 45 non-check callers keep fresh-read-every-call semantics. Coordinating: another agent holds src/frob/tickets/_leases.py for a test regression, so this fix stays in _archive.py (not _leases.py).