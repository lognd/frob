## Done report

Built the ordered call graph substrate T-0746's own disclosure asked for
and wired it into a new per-call-site ordering rule (PROTO004) in
frob.gates._protocol_summary.

frob.graph.callgraph gains OrderedCallGraph (a Caller symref -> callee
symrefs mapping that preserves source-text call order, duplicates
included) and build_ordered_call_graph, which resolves callees with the
same T-0841 language-correct privacy rule build_call_graph now uses. A
private extractor, _ordered_called_names, mirrors _called_names but
returns an ordered tuple instead of a frozenset -- deliberately a
parallel extractor, not a replacement, so build_call_graph's existing
unordered contract (every other consumer: frob.dup, DEAD001, PROTO001-3)
is untouched.

frob.gates._protocol_summary gained PROTO004: for every function in a
tagged package (not just protocol-tagged entrypoints), it walks that
function's OWN ordered call sequence, tracking which protocol states are
established SO FAR by earlier calls in that exact sequence (seeded from
each protocol's declared initial state, grown by each earlier callee's
transitive FunctionSummary.transitions). A call to a frob:requires-tagged
callee whose precondition is not yet established on that sequence is an
ERROR (same waiver/discharge posture as PROTO002/PROTO003) -- this is
the crisp case PROTO002's own existential approximation structurally
cannot catch: a state that IS established somewhere in the package
closure, just too late relative to this specific call.

DISCLOSED SCOPE (not silently papered over): this is SEQUENCE-sensitive
within one caller's own body, not full branch-aware path-sensitivity --
a call inside an untaken if/else branch is treated as if it always
executes (RawSymbol.body_tokens has no control-flow structure to read).
This narrows T-0840's own crisp target (same-body ordering bugs) but
does not close full path-sensitivity; real branch-aware analysis is
still future work, same false-negative/false-positive-direction
disclosure posture every other approximation in this module already
carries. New tests demonstrate PROTO004 catching exactly the case
PROTO002 misses (test_call_before_establishing_transition_is_an_ordering_error)
and staying silent on the corrected order and on a language-excuse
discharge.

Shared mechanism disclosure (T-0841 pairing): protocol_summary_gate's
per-package loop now also builds an OrderedCallGraph and widens
compute_protocol_summaries' summary roots to include every caller found
in it (not just tagged entrypoints) so PROTO004 has FunctionSummary data
for plain, untagged callers standing between two tagged functions --
this only widens summary coverage, it does not change any existing
summary's computed value (verified via the full existing PROTO001-003
test suite passing unchanged).

Scope-lease note: tests/test_gates.py and tests/test_graph.py were
scope-added to T-0840 to bind evidence; T-0841's own new tests share
those same two files but the per-file lease is exclusive, so T-0841's
Rust/TypeScript test additions carry their own frob:ticket T-0841
directive and a disclosed frob:waive SCOPE001 (both files, both
directions) explaining the sibling-ticket sharing arrangement -- same
ad-hoc-waiver precedent already used elsewhere in this repo for a
tests/**-leased-by-another-ticket situation (test_registry_*.py's T-0407
waivers).

Cuts: real branch-aware (if/else) path-sensitivity is NOT built here --
T-0840's own ticket text named "an ordered call graph plus a per-call-
site dataflow pass" as the target; the ordered call graph and the
per-call-site pass are both built, but the pass is sequence-only, not
control-flow-aware. Flagged for a future ticket if the user wants true
branch-level precision (would need a control-flow graph extraction this
repo's tree-sitter-token-stream substrate does not currently produce).
Filed no new ticket for this since it is exactly the gap T-0840's own
docstring already names as its own boundary, not a newly discovered
issue.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestProtocolOrderingGate::test_call_before_establishing_transition_is_an_ordering_error` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolOrderingGate::test_call_after_establishing_transition_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolOrderingGate::test_python_with_block_discharges_the_ordering_violation` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCallGraph::test_build_ordered_call_graph_preserves_source_text_call_order` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCallGraph::test_build_ordered_call_graph_resolves_a_rust_private_callee` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
