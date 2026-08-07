## Done report

New `frob.graph._generated.is_generated_source(root, path)` +
`GENERATED_MARKER_RE` scan a file's first ~20 lines for a generated-by /
`@generated` / `DO NOT EDIT` header (covering `frob exports` / `frob deploy
generate` output and the common Go/protobuf convention). `_cov001` in
`src/frob/gates/__init__.py` exempts a marked file from the COV001 frob:doc
obligation, memoized per path. Deliberately NARROWER than `[graph] exclude`:
the file stays fully in the graph so xref/dup/arch keep seeing its symbols;
only the hand-documentation obligation is waived. Documented under
`docs/modules/graph.md#generated-file-marker`. Tests:
`tests/test_graph.py::TestGeneratedSource` (marker detector) and
`tests/test_gates.py::TestCoverageGate` (COV001 exemption + control).
Coordinator: minor bump 0.16.0 -> 0.17.0 (new public API), release
re-stamped. Also filed T-0336 for a real TEST001/002 edge-keying bug found
en route (explicit frob:tests unit edges keyed by target not src, so they
only pass via the naming-convention fallback).
