## Done report

Implemented the comment-DSL declaration surface for typestate protocols
(T-0739 child 1): frob:protocol NAME states="..." initial="..."
[cleanup="always"|"on-error"|"process-exit-ok"], frob:transition
proto="NAME" from="S" to="T", and frob:requires proto="NAME" state="S",
all parsed into new EdgeKind.PROTOCOL/TRANSITION/REQUIRES edges.
frob:transition/frob:requires have no bare target token -- their grammar
is all key="value" attrs, and the edge target becomes the parsed proto=
attribute (frob.graph.dsl._ATTR_ONLY_VERBS special-case in _parse_line).

Added the zero-declaration init/deinit name-pattern convenience: a bare
<prefix>_init/<prefix>_deinit function pair in the same file (also
open/close, acquire/release, frob.graph.dsl._INFER_PAIRS) implicitly
synthesizes a 3-state uninitialized->active->closed protocol with no
frob:protocol comment at all (_infer_init_deinit_protocols), each
synthesized edge carrying inferred="true". Inference is scoped to
exactly these declared name pairs, never a general machine-inference
heuristic, per the ticket's explicit limit.

Implemented the ENFORCEABILITY requirement: a frob:protocol bound by
zero frob:transition/frob:requires edges in the same file is itself a
MalformedDirective (_protocol_coherence, mirroring the existing
frob:debt/frob:todo coherence pass). This scope is per-file, matching
every other DSL-layer coherence check (_debt_todo_coherence) -- a
protocol declared in one file and bound entirely from another still
reads as unbound in this pass; cross-file tallying is explicitly left
to a later T-0739 child (the graph-wide verification engine), noted in
both the code comment and docs/modules/gates.md.

No frob.gates change was needed: every MalformedDirective this surface
produces (missing/invalid protocol/transition/requires attrs, an
unbound protocol) already falls through the existing DSL001 generic
catch-all rule (any malformed frob: directive not claimed by a
per-flavor rule id), so a malformed or unbound protocol declaration
fails frob check today with zero gates.py changes.

Documented the full grammar, the zero-declaration inference rule, the
per-file enforceability check and its cross-file limitation, and the
DSL001 routing in docs/modules/gates.md under a new "Typestate protocol
declarations (T-0744)" section, following the existing DEBT/DEPRECATED
gate section format.

Deviation from a literal reading of the ticket's own grammar sketch:
"frob:transition proto=NAME from=S to=T" as written looks attr-style
throughout (no bare target), which is what got implemented; frob:protocol
kept the DSL's normal "bare target then attrs" shape (frob:protocol NAME
states=... initial=...) since NAME reads naturally as a plain target
token there, consistent with every other existing verb.

### Changed
```
 docs/modules/gates.md        |  59 +++++++++++
 src/frob/graph/_models.py    |  15 +++
 src/frob/graph/dsl.py        | 242 ++++++++++++++++++++++++++++++++++++++++++-
 tests/unit/graph/test_dsl.py | 164 +++++++++++++++++++++++++++++
 4 files changed, 475 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_declared_protocol_round_trips` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_protocol_missing_states_is_malformed` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_protocol_initial_not_in_states_is_malformed` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_protocol_bad_cleanup_is_malformed` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_transition_missing_attrs_is_malformed` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_requires_missing_state_is_malformed` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_unbound_protocol_is_a_loud_error_not_a_skip` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_bound_protocol_is_not_flagged_unbound` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestInitDeinitInference::test_init_deinit_pair_infers_a_protocol` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestInitDeinitInference::test_open_close_pair_also_infers` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestInitDeinitInference::test_unpaired_init_infers_nothing` (pytest node id, verified passing when recorded)
