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

### Changed
```
 tickets/T-1135/ticket.md      |  4 ++-
 tickets/T-1137/ticket.md      |  4 ++-
 tickets/T-1219/done-report.md | 81 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-1219/ticket.md      | 14 +++++++-
 tickets/T-2468/ticket.md      |  2 +-
 5 files changed, 101 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte` (pytest node id, verified passing when recorded)
- `tests/unit/test_capability_native.py::TestScanPythonCapabilitiesParity::test_this_repos_own_capability_python_module_matches` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity::test_this_repos_own_arch_python_module_matches` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScan::test_docstring_query_still_finds_real_docstrings` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOCENUM001@docs/modules/gates.md, DRIFT002@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1135/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1135/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1135/src/frob/gates/_dup_graph_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1135/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-1135/src/frob/vet/_capability.py, GATERULE001@src/frob/gates/_gates_schema.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md, missing-argument@tests/unit/test_ticket_runner_land_release.py


frob:no-behavior-change reason="epic-rollup close: T-1219's 4 children (T-1220..T-1223) already shipped and archived done; this ticket only records the rollup Done report and closes the umbrella, no new code"
