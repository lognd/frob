## Done report

Wired Rust/C++/TypeScript language-excuse discharge into a real
cross-file call-graph scan, per T-0746's own disclosure -- the root
cause was that frob.graph.callgraph's callee-privacy check hardcoded
Python's leading-underscore naming convention instead of reading each
frob.lang grammar walker's own, already-correct RawSymbol.public field.

frob.graph.callgraph._short_name_index now computes is_private as
`not sym.public` instead of `_short_name(sym.qualname).startswith("_")`.
For Python these are identical (frob.lang._walk_python's own public rule
IS that exact check), but for Rust (pub/PyO3-export), C++
(access_specifier/file-scope static), and TypeScript (export/
accessibility_modifier) the naming heuristic was simply wrong -- a
private Rust helper with no leading underscore (a normal Rust idiom)
previously got NO edge at all. This one change is what actually wires
every frob.lang-supported language into a real call-graph scan; no new
per-language call-graph implementation was built, matching the ticket's
own "mirror T-0745's own T-0809 disclosure pattern rather than silently
building a second, unreviewed call-graph substrate" instruction.

frob.gates._protocol_summary's `.py`-only filters (tagged-package
grouping, _package_edges) are lifted to every frob.lang.
supported_extensions() file. `_discharge` now dispatches through a new
_language_discharge/_DISCHARGE_BY_SUFFIX table to
rust_drop_discharge/cpp_raii_discharge/typescript_using_discharge by the
tagged symbol's file extension, not just python_with_discharge --
PROTO002/PROTO003 now get real discharge coverage for all four
predicates T-0746 built but only wired one of.

DISCLOSED SCOPE: `mark_unresolved`'s own "does this call target LOOK
unresolved" heuristic (frob.graph.callgraph.build_call_graph) is still
Python-naming-specific (it scans a bare call-token's spelling, which is
all a flat token stream offers -- there is no RawSymbol for an
unresolved callee to read .public off of) -- a genuinely dangling
private call in a non-Python file whose name does not start with `_`
will not be flagged UNRESOLVED_CALLEE. This is the same false-negative-
biased direction every other best-effort rung in this module already
accepts and is explicitly disclosed in both callgraph.py's and
_protocol_summary.py's docstrings; not closed by this ticket.
gc_finalizer_discharge has no dispatch entry (no GC-language grammar in
frob.lang today) -- stays built/tested for when one is added, per its
own module's doctrine; not a gap this ticket needed to close.

New tests: a Rust file end-to-end PROTO002 scan (no discharge -> ERROR),
a Rust Drop-impl discharge (-> WARN not ERROR), a TypeScript using-block
discharge (-> WARN not ERROR), plus two frob.graph.callgraph tests
proving a Rust private helper WITHOUT a leading underscore now resolves
(and a pub one still does not) -- the exact false-negative this ticket
closes.

Shared-mechanism disclosure (T-0840 pairing): protocol_summary_gate's
per-package loop is shared with T-0840's PROTO004 ordering check (both
land in the same function); T-0841's own is_private fix is what makes
T-0840's build_ordered_call_graph correct for non-Python languages too
(same _short_name_index it reuses), disclosed in both Done reports.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestProtocolVerificationGate::test_rust_file_state_never_established_is_an_error` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolVerificationGate::test_rust_drop_impl_discharges_the_requirement` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolVerificationGate::test_typescript_using_discharges_the_requirement` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCallGraph::test_build_call_graph_resolves_a_rust_private_callee_by_pub_keyword` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCallGraph::test_build_call_graph_does_not_resolve_a_rust_pub_callee` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
