---
id: T-2363
title: 5-package import cycle (serve/stats/tickets/testing/app) needs an owner decision
  on which dependency to invert
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/serve/_tools.py
- src/frob/stats/__init__.py
- src/frob/tickets/_land.py
- src/frob/testing/_coverage_wait.py
- src/frob/app/_daemon_proxy.py
- src/frob/__init__.py
evidence_scope:
- tests/unit/test_capability_and_deploy_cycle_regression.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/__init__.py
  reason: the CYCLE001 declaration comment for the 160-node SCC lives at its representative
    (lowest-sorted) file, src/frob/__init__.py; frob:waive CYCLE001 there does nothing
    (see T-2584) so the declaration is a plain doc comment instead
  actor: logan
  at: '2026-08-18'
body_changes:
- mode: append
  reason: 'BUG002 fired because this bug-kind ticket is a documentation-only declaration
    with no behavior change; recording the frob:no-behavior-change directive per the
    land error''s own remedy #2'
  actor: logan
  at: '2026-08-18'
  old_length: 3306
  new_length: 4123
evidence:
- tests/unit/test_capability_and_deploy_cycle_regression.py::TestPlantedCycleStillDetected::test_planted_two_node_cycle_is_detected
designated_repro_test: null
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: f68fd921ca4b105e6807729899045a708d9a2eca
---
T-2358 measurement (2026-08-18): the ERROR-severity import cycle
originally described as "serve <-> stats" is actually a 5-package
strongly-connected component (177 nodes at first measurement, 175 after
T-2358 removed 2 unrelated members via its own deploy/vet fixes).

Traced with this repo's own cycle tooling
(frob.check._python._build_import_graph + frob.cycle.graph.find_cycles,
BFS over the SCC from tickets/__init__.py to the nearest serve node --
not guessed):

    serve/_tools.py           -> stats/__init__.py
    stats/__init__.py         -> tickets/__init__.py
    tickets/_land.py          -> testing/__init__.py
    testing/_coverage_wait.py -> app/_daemon_proxy.py
    app/_daemon_proxy.py      -> serve/__init__.py   (closes the loop)

Each edge, read in isolation, looks like ordinary top-down usage:
- serve/_tools.py calling a stats helper (an MCP tool surfacing stats)
- stats/__init__.py using TicketQueue/load_queue (frob.tickets)
- tickets/_land.py using a testing utility during land verification
- testing/_coverage_wait.py shelling out via the daemon proxy
- app/_daemon_proxy.py starting/managing the serve daemon

The cycle exists only because these five packages' dependencies, taken
together as a whole, form a ring with no single edge that is obviously
"the wrong one" in isolation. WHY THIS NEEDS A REAL DECISION, NOT A GUESS
(per explicit owner instruction on T-2358, quoted verbatim: "if that
decision is not obvious, stop and tell me rather than guessing; I would
rather own that call than have it made implicitly"): breaking this means
choosing ONE of the five edges to invert (dependency injection), extract
(shared module, same pattern T-2358 used for its own two fixes), or
remove (maybe one of these usages is avoidable) -- and each candidate
touches a DIFFERENT package's public surface and a different design
tradeoff:

- Does serve/_tools.py really need to call into stats directly, or
  should the MCP tool layer take a stats snapshot as a parameter?
- Should stats depend on tickets at all, or should ticket data be passed
  in rather than pulled?
- Does tickets/_land.py's use of a testing utility belong in tickets, or
  should that verification step live in testing/app instead?
- Does testing/_coverage_wait.py genuinely need the daemon proxy, or is
  there a narrower serve-control primitive that doesn't pull in all of
  serve/__init__.py?
- Should app/_daemon_proxy.py depend on all of serve/__init__.py, or a
  narrower daemon-control leaf module?

REQUIRED once a direction is chosen: do NOT break this by moving an
import inside a function purely to silence the detector -- T-2358 found
exactly that anti-pattern already in place for the deploy/vet cycles
(commented "avoid a circular import") and it did not even work (the
detector still caught both). A deliberately planted 2-node cycle test
(T-2358's own `tests/unit/test_capability_and_deploy_cycle_regression.py
::TestPlantedCycleStillDetected`) must still pass after whatever fix
lands here, proving the fix did not blind the detector.

Positive controls once scoped:
1. `frob cycle src/frob` reports zero import cycles (the ORIGINAL T-2358
   acceptance criterion this ticket finally satisfies).
2. The planted-cycle test above still passes.
3. Full test suites for every touched package pass.

frob:no-behavior-change reason="this ticket declares a live 160-node CYCLE001 import cycle (T-2358 measurement, re-verified and expanded here) rather than structurally fixing it -- the repo owner explicit standing instruction is not to guess which of several package-boundary edges to invert. The only change is a documentation comment at src/frob/__init__.py explaining the decision and pointing at the two follow-up tickets (owner-decision T-2583, and a separately-scoped CYCLE001-waiver-wiring gap T-2584 found while attempting the normal frob:waive suppression and confirmed inert). No runtime behavior changes; the bound evidence (the T-2358 planted-cycle regression test) is a positive control on the detector itself, not a fix-behavior test, since there is no fix in this change to test."