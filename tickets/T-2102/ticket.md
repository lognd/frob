---
id: T-2102
title: frob's self-model test asserts hardcoded golden node/flow/claim counts that
  drift on every organic model growth (23-vs-25 nodes)
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
- text: Given design/frob.strata's live elaborated model, when test_parses_and_elaborates
    and test_every_claim_proves run, then both pass against the current model and
    the fix decides+documents whether counts are re-measured exact values or replaced
    by a non-decreasing structural invariant
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
Sibling investigation ticket to T-2101 (which fixes the unrelated
duplicate-node-id ERROR seen at land time -- see T-2101's own body for
why the two are separate defects, not one).

`tests/system/test_frob_self_model.py::TestFrobSelfModel::
test_parses_and_elaborates` asserts `len(_model.nodes) == 23`,
`len(_model.flows) == 44`, `len(_model.boundaries) == 1`,
`len(_model.claims) == 31` against `design/frob.strata` parsed alone
(no merge, no litmus involvement -- confirmed unrelated to T-2101).
Measured directly: the live model elaborates to 25 nodes today, not 23
-- 2 real, organic nodes were added to `design/frob.strata` since this
docstring was last hand-updated. `test_every_claim_proves` (same file)
also fails; it asserts `len(claim_results) == 31` off the same stale
model and is very likely the exact same drift, not a separately
root-caused issue (both counts move together whenever a node/flow gains
a `may` capability that drags in a THREAT003 discharge claim -- the
model growth is the single common cause).

This docstring's own multi-paragraph running commentary already shows
this "landed a node, forgot to bump the golden counter" pattern
recurring repeatedly: T-0707 (`fleet`), T-0864 (`natives`), T-1329
(`refactor`), T-1591 (`security`), T-1735 (`verify`) -- each one a
separate ticket's Done report disclosing the SAME kind of miss. A
hardcoded exact count that must be hand-rederived every time the
self-hosting model legitimately grows is a standing maintenance trap,
not a one-off oversight.

Decide (and implement) whether these assertions should:
(a) simply be bumped to the current measured counts (23->25 etc.,
    matching the pre-T-2097 precedent every prior ticket in this
    docstring's history already followed), continuing to accept the
    hand-rederivation cost each time the model grows, or
(b) be replaced with a structural invariant that does not require a
    manual bump on every legitimate model addition -- e.g. a floor
    (`>=` the last known count, catching only SHRINKAGE/regression,
    never organic growth) plus a positive-count sanity check, since
    `elaborate` already fails closed on a real corruption (duplicate
    ids, dangling references) and this test's OWN purpose (per its
    module docstring) is "the model is a real, live program that
    parses/elaborates/proves its claims," not "the model has exactly N
    components."

Whichever is chosen, `test_every_claim_proves`'s `assumed_ids`/
`proved_ids` sets (or its own count assertion) need the same
treatment, re-measured against the CURRENT model, not assumed to
already be correct.
