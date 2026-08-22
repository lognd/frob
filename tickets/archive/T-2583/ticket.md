---
id: T-2583
title: 'Owner decision needed: pick which edge to invert to break the 160-node serve/stats/tickets/testing/app
  import cycle'
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
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/serve/_tools.py
- src/frob/stats/__init__.py
- src/frob/tickets/_land.py
- src/frob/tickets/_archive.py
- src/frob/testing/_coverage_wait.py
- src/frob/app/_daemon_proxy.py
- docs/modules/stats.md
- src/frob/app/stats_runner.py
- tests/test_stats.py
- docs/modules/serve.md
- tickets/T-2667/ticket.md
evidence_scope:
- tests/test_stats.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/stats.md
  reason: T-2583's candidate-2 fix touches stats.md (signature doc), stats_runner.py
    (collect() caller), test_stats.py (evidence tests), and serve.md (frob_stats doc,
    AFFECT001 closure)
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/app/stats_runner.py
  reason: T-2583's candidate-2 fix touches stats.md (signature doc), stats_runner.py
    (collect() caller), test_stats.py (evidence tests), and serve.md (frob_stats doc,
    AFFECT001 closure)
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/test_stats.py
  reason: T-2583's candidate-2 fix touches stats.md (signature doc), stats_runner.py
    (collect() caller), test_stats.py (evidence tests), and serve.md (frob_stats doc,
    AFFECT001 closure)
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/modules/serve.md
  reason: T-2583's candidate-2 fix touches stats.md (signature doc), stats_runner.py
    (collect() caller), test_stats.py (evidence tests), and serve.md (frob_stats doc,
    AFFECT001 closure)
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tickets/T-2667/ticket.md
  reason: residue ticket filed from this ticket's own investigation; SCOPE001 flags
    the new file
  actor: logan
  at: '2026-08-19'
body_changes:
- mode: append
  reason: 'owner decision: break at candidate 2 (stats/__init__.py)'
  actor: logan
  at: '2026-08-19'
  old_length: 2673
  new_length: 5191
evidence:
- tests/test_stats.py::test_collect_injected_queue_matches_direct_ticket_stats
- tests/test_stats.py::test_collect_with_no_queue_reports_empty_ticket_stats
designated_repro_test: tests/test_stats.py::test_collect_injected_queue_matches_direct_ticket_stats
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: d1d5d7e9ab1c9b28628f89a6611fc1f820829e82
---
T-2363 measured and DECLARED (frob:waive CYCLE001 at src/frob/__init__.py) a 160-node cross-package SCC rather than guessing which edge to break, per the repo owner's explicit standing instruction to not guess on this kind of call.

Re-measurement (frob.check._python._build_import_graph + frob.cycle.graph.find_cycles against the real src/ tree) found the SCC is bigger than T-2358's original simplified 5-edge description: serve/_tools.py has a SECOND, independent module-level edge into frob.tickets (line 24, 'from frob.tickets import doable, load_queue') that does not route through frob.stats at all, so cutting only the stats->tickets edge would not collapse the cycle.

Candidate edges to invert/extract, each a different package's public surface:
1. serve/_tools.py's two ticket-queue imports (direct at line 24, and via frob.stats) -- MCP tools would need ticket data injected rather than self-loading it.
2. stats/__init__.py's 'from frob.tickets import TicketQueue, TicketState, load_queue' -- TicketQueue/TicketState already live in tickets/_models.py (NOT in this SCC), so switching to a direct type-only import from there is free; load_queue's home (tickets/_archive.py) IS in the SCC, so collect() would need the caller to load the queue and inject it.
3. tickets/_land.py's function-local 'from frob.testing import collect_python_tests' (~line 4765) -- a genuine runtime need during land's orphaned-evidence check, not an accidental import.
4. testing/_coverage_wait.py's function-local 'from frob.app._daemon_proxy import ...' (line 163) -- the daemon-lease fast path, deliberately deferred already.
5. app/_daemon_proxy.py's several function-local 'from frob.serve import ...' (lines 122/207/287/399/443) -- the daemon proxy's whole job is talking to frob.serve's socket daemon, so this edge is closer to inherent than accidental; the honest fix is extracting shared daemon-protocol primitives (socket_path, send_request, DaemonError, SocketDaemonConfig, run_socket_daemon) into a neutral module both app and serve import, mirroring T-2358's own deploy/_generate_common.py extraction pattern.

None of the five is obviously correct without a real architectural call from the owner. Do NOT fix this by moving an import inside a function purely to silence the detector -- T-2358's own regression test proves the detector already walks into function bodies, so that anti-pattern does not even work.

Acceptance: owner picks a direction (or explicitly re-affirms the declaration), then whichever structural fix is chosen lands, frob check --only cycle goes clean on this SCC, and the frob:waive CYCLE001 at src/frob/__init__.py is removed in the same change.


## OWNER DECISION (2026-08-19): break the cycle at candidate 2

The repo owner picked **candidate 2 -- `stats/__init__.py`'s
`from frob.tickets import TicketQueue, TicketState, load_queue`**.

This ticket is no longer a decision ticket. Implement that break.

Why this one, per the ticket's own analysis: it is the cheapest real cut.
`TicketQueue`/`TicketState` already live in `tickets/_models.py`, which is
NOT in the SCC, so retargeting those two to a direct type-only import is
free and breaks nothing. Only `load_queue` (whose home
`tickets/_archive.py` IS in the SCC) needs real work -- `collect()` must
take the queue from its caller rather than loading it itself.

### What "done" requires

- `frob check --only cycle` is CLEAN on this 160-node SCC
- the `frob:waive CYCLE001` at `src/frob/__init__.py` is REMOVED in the
  same change. A structural fix that leaves the waiver behind has not
  discharged anything, and a stale waiver whose premise expired is a
  documented failure class in this repo (T-2612 found 12 of them, 9 hiding
  real work)
- `frob cycle src/frob`, `frob cycle src`, and `frob cycle .` all agree
  (T-2588 fixed the path-shape false-clean; do not regress it)

### Constraints

- Do NOT move an import inside a function to silence the detector.
  T-2358's own regression test proves the detector walks into function
  bodies, so it does not even work.
- Injecting the queue into `collect()` changes a public signature. Find
  every caller (`frob explore xref collect`) and update them in the same
  change; a partially-updated call graph is worse than the cycle.
- Candidate 5 (`app/_daemon_proxy.py` -> `frob.serve`) is explicitly NOT
  in scope here. The owner may take it later; its honest fix is extracting
  shared daemon-protocol primitives into a neutral module, not inversion.
  If breaking candidate 2 turns out to leave the SCC intact because
  candidate 5 also closes a loop, report that with the re-measurement and
  file candidate 5 separately -- do not silently widen.

### Positive controls, both directions

- the SCC is gone from `frob check --only cycle` AND from `frob cycle` on
  all three path shapes
- `frob.stats.collect()` still returns identical results for the same
  queue -- inject it in tests and compare against the pre-change output
- a deliberately re-added `from frob.tickets import load_queue` in
  `stats/__init__.py` makes CYCLE001 fire again, proving the detector is
  still watching this edge rather than the waiver having been what
  silenced it