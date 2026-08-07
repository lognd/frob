## Done report

Implemented both open candidates from T-0297's original three-part idea
(COV005 shipped candidate (a) already):

COV006 (warn): a `frob:tests` edge bound to a PRIVATE symbol whose test
has no reachability to it via `frob.graph.callgraph` (T-0288/T-0290's
shared call-graph substrate, reused exactly as-is -- no second traversal
implementation). Restricted to PRIVATE targets only, because
`build_call_graph` never records an edge to a PUBLIC callee by
construction; checking a public target would always misreport
"unreachable" regardless of the real binding, which would be unsound, not
merely noisier. Memoizes call-graph builds per (test_file, target_file)
pair within one gate run (`graph_cache`) -- an earlier unmemoized version
cost 28s in the coverage stage on this repo (thousands of frob:tests
edges reparsing the same file pairs); memoized it dropped to ~2.5s,
matching the other COV checks' cost.

Disclosed, not silently tuned away: COV006 has a real, common
false-positive shape on THIS repo's own test suite -- a test that reaches
its bound private helper only indirectly, via a public wrapper in the
same file that itself calls the helper, is reported unreachable, because
`build_call_graph` never records an edge into a public callee at all (no
edge for that first hop, so `closure` cannot walk through it). This is
not a traversal bug; it is the same public-boundary-stop behavior
T-0288/T-0290 depend on, reused unmodified per this ticket's instruction.
97 COV006 findings on this repo today are mostly this shape (many
`frob:tests` bindings to private gate helpers whose tests call the public
`coverage_gate`/`test_gate` wrapper, not the private helper by name).
Warn severity reflects exactly this: a prompt to double check, not proof
of a bad binding -- matches the ticket's own "warn-severity first (repo
adoption cliff)" instruction.

COV007 (warn): a `frob:doc` edge whose src symbol is PRIVATE. ~61
findings on this repo today, some of which are legitimate (e.g.
`frob.logging._FrobFormatter`, `frob.gates._pii_structural._FieldSignature`
are private classes this repo deliberately documents) -- COV007 flags the
pattern for a human decision (move the anchor to the public caller, or
confirm the private helper genuinely needs its own anchor), it does not
forbid it.

Both new rules registered in `_KNOWN_GATE_RULES` so `frob:waive
COV006/COV007 reason="..."` is a real, effective waiver (WAIVE002-safe),
not silently ineffective.

Fixed a self-inflicted bug found before landing: an inline code comment
("# frob:doc-on-private-helper (COV007)") accidentally matched the
`frob:<verb>` directive line pattern and was rejected as an
unknown-verb MalformedDirective -- reworded to keep "frob:" out of
line-start position in plain comments.

### Changed
```
 docs/modules/gates.md      |  89 +++++++++++++++++
 src/frob/gates/__init__.py | 237 ++++++++++++++++++++++++++++++++++++++++++++-
 tests/test_gates.py        | 195 +++++++++++++++++++++++++++++++++++++
 3 files changed, 520 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates.py::TestCoverageGate::test_cov006_flags_test_with_no_call_graph_reachability` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov006_silent_when_test_calls_the_bound_symbol` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov006_never_fires_for_a_public_target` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov007_flags_doc_anchor_on_private_helper` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov007_silent_for_doc_anchor_on_public_symbol` (pytest node id, verified passing when recorded)
