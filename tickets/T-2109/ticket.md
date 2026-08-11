---
id: T-2109
title: Self-model node-count floor should be a derived expectation, not a >= floor
  (unintended growth passes silently)
state: queued
kind: bug
origin: agent
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/system/test_frob_self_model.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: Given design/frob.strata's raw pre-elaboration node/store/cache/queue/cdn/balancer
    declaration counts, when test_parses_and_elaborates runs, then the elaborated
    node count is asserted equal to the SUM of those raw counts (a derived, recomputed
    expectation) rather than a hardcoded floor, so an unintended node addition fails
    loudly
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
Follow-up to T-2102, per explicit coordinator review: T-2102 replaced
`test_parses_and_elaborates`'s hardcoded `== 23` node-count golden with
a `>= 25` floor. A floor is asymmetric -- it catches SHRINKAGE (a real
regression) but NOT an unintended node/flow/claim being added that no
ticket meant to introduce, which is a real failure mode for a self-
describing model.

Investigated first, per the coordinator's own framing, whether anything
else already covers the growth direction: searched `frob.gates._sys`
(SYS001-004: dangling directive, unbound boundary/secret, undeclared
cross-component import, design-file load failure) and the
scope/ticket-citation gates. Nothing structurally validates that a
PLAIN node (no boundary/secret role, no `may` capability) is
intentional -- SYS002 only requires a boundary/secret construct to have
a code binding, not that a node's mere existence was deliberate.
`design/frob.strata` is an ordinary git-tracked file, so a diff to it
is visible at land/review time, but that is human review, not a static
check. Conclusion: nothing else covers this direction; the floor
genuinely leaves it open.

Fix, per the coordinator's own suggested shape (converting a golden
into an invariant, the same move already made for `test_every_claim_
proves`'s `proved_ids`): replace the node-count floor with a DERIVED
expectation, recomputed from the design source's own pre-elaboration
declarations rather than hand-maintained.

Measured directly (`parse_module` before `elaborate`, same
`design/frob.strata`): 23 hand-declared `node` decls in the raw AST,
25 nodes after elaboration -- the +2 is `frob.strata._design_load`'s
own documented desugar behavior ("a store desugars into a plain Node
at elaborate time," `store_ids` docstring), specifically the model's 1
`store` (-> `tickets_ledger`) and 1 `cache` (-> `graph_cache`)
declarations, confirmed by diffing the raw vs. elaborated node id sets
directly (`{'tickets_ledger', 'graph_cache'}`, exactly the 2 extra).
`queue`/`cdn`/`balancer` decls desugar into nodes the same way per the
same module's own architecture (0 of each in the current model, so
untested by THIS measurement, but documented identically) -- the
derived formula sums all five std.infra decl kinds for robustness
against a future one being added, not just the two currently nonzero.

Scope is the node-count assertion specifically -- the coordinator's
example ("a node that no ticket introduced") is about nodes, the
literal 23-vs-25 example this whole investigation started from. Left
flows/boundaries/claims as the T-2102 floor: those are NOT proven to
follow a simple derivable formula (`raw_flows=42` vs `elaborated_
flows=44` -- a +2 that looks like 1 synthesized flow per store/cache,
but that specific per-decl multiplier was not independently verified
against the elaborator's own synthesis code beyond this one
measurement, and guessing wrong here would make the test WRONG rather
than merely weak, a worse failure mode than the floor it would
replace).

## Failure log
- 2026-08-10 attempt 1: Derived-formula approach empirically proven useless: recomputing expected node count from the SAME raw design source that would carry the unintended addition means both sides of the equation move together -- verified directly by injecting an unintended node into design/frob.strata and re-running the test, which still passed. No fix landed; keeping T-2102's floor as-is per coordinator direction to push back rather than force a broken change.
