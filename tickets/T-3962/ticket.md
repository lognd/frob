---
id: T-3962
title: 'invariant obligation: forbidden-constant reachability'
state: queued
kind: invariant
origin: agent
created: '2026-09-06'
priority: high
parent: T-3942
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_design_invariants.py
- src/frob/graph/callgraph.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a module-level frozenset named matching *_FORBIDDEN/*_EXCLUDED/*_ALLOWED
    and a declared sink it must guard, when a call-graph path from a declared entrypoint
    to that sink never references the frozenset, then the new invariant obligation
    fires naming the unguarded path
  evidence: []
- text: given the existing COV006 BFS reachability code in callgraph.py, when this
    obligation is implemented, then it reuses that machinery rather than adding a
    second call-graph traversal
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-175 (T-3942 item 1). The consumer explicitly asserts frob ALREADY HAS the machinery this needs: call-graph reachability via a frob:invariant plus frob check --only invariant. PARTIALLY VERIFIED: src/frob/gates/_cov006_third_file_reachable and the COV006 rule (frob:tests call-graph reachability, T-0483) do bounded-BFS reachability over the private-callee call graph (src/frob/graph/callgraph.py) -- so the underlying callgraph/reachability primitive frob would need is proven to already exist and be reused across gates. It is wired for TEST reachability (COV006), not for a security-constant-guard obligation; no existing rule currently checks "is this frozenset consulted on every path to its sink."

FINDING THIS WOULD HAVE CAUGHT: EXCLUDED_TABLES/FORBIDDEN_COLUMNS checked on three write paths and skipped on the fourth (revert_change). Generalise as a frob:invariant obligation form: a module-level frozenset named matching *_FORBIDDEN/*_EXCLUDED/*_ALLOWED must be read (referenced) on every call-graph path from a declared set of entrypoints to the sink function it guards. Reuse the existing callgraph.py reachability machinery (the same BFS used by COV006) rather than building new call-graph code -- this is the specific thing to verify before building, and it is TRUE: the machinery exists, only the obligation form (a new frob:invariant flavor, not a new graph engine) is missing.
