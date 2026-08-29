---
id: T-3424
title: 'T-3260''s vmodel split changed the FFI edge payload shape: edges gained an
  attrs field, breaking the round-trip assertion'
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
T-3260's split of `strata-core/src/graph/vmodel.rs` changed the SHAPE of the
vmodel edge payload crossing the Rust-to-Python boundary: edges now carry an
`attrs` key that was not there before. A round-trip test asserting exact
equality caught it.

MEASURED 2026-08-29 on a quiet box, xdist -n 8, no coverage:

    tests/unit/strata/test_vmodel_authoring.py::TestVmodelAuthoringFormat
        ::test_vmodel_node_and_edge_round_trip_through_python

    assert ast["vmodel_edges"] == [
        {"kind": "satisfies", "src": "design_1", "dst": "req_1"}
    ]
    E  At index 0 diff:
       {'attrs': {}, 'dst': 'req_1', 'kind': 'satisfies', 'src': 'design_1'}
       != {'kind': 'satisfies', 'src': 'design_1', 'dst': 'req_1'}

The values all match. The only difference is an additional `attrs` key holding
an empty dict. `vmodel_nodes` round-trips fine in the same test -- the assertion
above it passes -- so this is specific to the edge payload.

FIRST QUESTION, AND IT DECIDES EVERYTHING: was adding `attrs` to edges
INTENDED? T-3260 was scoped as a pure line-count split of a file over the
LARGE001 threshold, described in its own report as a relocation with callers
unchanged. A payload gaining a field is not a relocation. Two possibilities and
they need opposite fixes:

  (a) INTENDED -- `attrs` genuinely belongs on edges (nodes already carry
      attrs, so parity is plausible) and the split was the occasion for adding
      it. Then the test's expectation is stale and should be updated, and
      T-3260's done report understated its own scope. Check whether anything
      CONSUMES edge attrs; a field nothing reads is not parity, it is
      unreferenced surface.
  (b) UNINTENDED -- a struct grew a serialized field as a side effect of being
      moved between modules (a derive, a default, a shared serializer picked up
      at the new location). Then the payload change is the defect and the test
      is right to fail.

DO NOT UPDATE THE TEST BEFORE ANSWERING THIS. Adding `"attrs": {}` to the
expected dict makes the failure disappear in about ten seconds and would
permanently hide whichever of (a) or (b) is true. This test exists precisely to
notice that the Rust-to-Python payload shape changed; a test that is edited
whenever it fires stops being that.

HOW TO ANSWER IT: read T-3260's diff for the edge struct and its serialization
(`strata-core/src/graph/vmodel/mod.rs`, `closure.rs`, and the parse side in
`strata-core/src/parse/grammar_vmodel.rs`). Compare the edge type's derives and
fields before and after. `git show` the pre-split file for the same struct. The
answer should be visible without guessing.

WIDER CHECK, worth doing either way: this test covers ONE payload shape. If a
struct gained a field in a move, others in the same split may have too, and only
this one had an exact-equality test pointed at it. Enumerate the types whose
serialization crosses the FFI boundary in the split files and confirm which are
covered by a shape assertion at all. Report the ones that are not -- an
uncovered payload shape is the gap that let this reach main.

NOTE ON ATTRIBUTION: T-3260 was a genuinely good piece of work -- it split two
Rust files along seams an earlier waiver had already identified, kept a flat
re-exported surface, and verified with cargo build/test/fmt/clippy plus a
native rebuild. This finding does not undo that. It does mean the split had a
behavioural component that its verification did not surface, and cargo tests
passing did not catch it because the assertion that noticed lives on the PYTHON
side of the boundary.

MUST-FIRE FIXTURE:   the edge payload shape crossing the FFI boundary is
                     asserted, and a spurious added field fails it.
MUST-STAY-QUIET:     a deliberate, consumed field addition passes once the
                     expectation is updated together with its consumer.

ACCEPTANCE
- (a)-vs-(b) answered with the diff cited, not inferred.
- If (a): the consumer of edge attrs named, or the field removed as unreferenced.
- If (b): the unintended serialization change reverted.
- The FFI payload-shape coverage enumeration reported.
