## Done report

: T-1219 EPIC perf: migrate tree-extraction layer to frob_core (Rust)

Four children rolled up, all done:

- T-1220: tree-extraction kernel (source bytes to symbols/spans/tokens/
  identifiers/comment+docstring) -- `frob-core/src/extract.rs`. Byte-for-
  byte parity with the Python extractor is verified by
  `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte`.
- T-1221: capability-scan resolver (import table + alias propagation) --
  `frob-core/src/capability_python.rs`. Parity verified by
  `tests/unit/test_capability_native.py::TestScanPythonCapabilitiesParity::test_this_repos_own_capability_python_module_matches`.
- T-1222: arch python metrics single-pass walk export (extraction only,
  rules stay in Python) -- `frob-core/src/arch_python.rs`. Parity
  verified by
  `tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity::test_this_repos_own_arch_python_module_matches`.
- T-1223: interim zero-Rust tree-sitter Query step for comment/docstring
  spans, shared across gates that need span-aware matching (opaque
  indirection, capability scan, fingerprint scan) -- landed as a
  Python-side change, no corresponding Rust file. This is consistent
  with the ticket's own title ("rust(interim)") and its explicit
  zero-Rust framing, not a gap: the epic's Rust-migration deliverables
  were 3 of 4 children (T-1220/1221/1222); T-1223 was always the
  Python-side comment/docstring-span primitive those three (and the
  gates consuming them) share, done as an interim step ahead of any
  further native migration. Verified by
  `tests/test_vet.py::TestCapabilityScan::test_docstring_query_still_finds_real_docstrings`
  and three sibling tests in the same class covering the enum-value
  false-positive, semicolon/comment-span exclusion, and comment-only
  needle cases.

Re-verified directly against the code, not just ticket state: `frob-core/
src/` contains `extract.rs`, `capability_python.rs`, `arch_python.rs` plus
`lib.rs` wiring them in; all four test files cited above exist in the
worktree. This matches the epic's own children-ranking in its body
("largest single native-cost family... not covered by frob_core today")
-- it now is.

This epic carries no formal `acceptance:` block (filed as a plain umbrella
ticket, not one with acceptance criteria written at file time), so there
is nothing to bind evidence to or amend -- only the rollup report and
close are needed, per the ticket's own shape.

## Filed

None -- no residue found. The FFI boundary requirement the ticket body
names (FFI001/FFI002) is satisfied by the existing native boundary in
`frob-core/src/lib.rs`; no new gap surfaced during re-verification.

## Cuts

None disclosed as outstanding beyond the T-1223 framing already
addressed above.

### Changed
(no changed files detected -- this ticket only closes an already-shipped
epic; the code changes were made and evidenced by its four children)

### Evidence
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte`
- `tests/unit/test_capability_native.py::TestScanPythonCapabilitiesParity::test_this_repos_own_capability_python_module_matches`
- `tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity::test_this_repos_own_arch_python_module_matches`
- `tests/test_vet.py::TestCapabilityScan::test_docstring_query_still_finds_real_docstrings`
