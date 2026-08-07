## Done report

Portion delivered (this dispatch, still NOT closing T-1220): the rust
companion kernel to the python slice landed earlier under this same
ticket -- second coherent vertical slice, per the ticket's own scoping
(cpp/typescript kernels and the consumer rewiring remain future work).

1. frob-core/Cargo.toml + Cargo.lock: added `tree-sitter-rust@0.24.2`
   (crates.io; no newer release pins cleanly against this crate's
   `tree-sitter@0.25.0` core at time of writing -- verified the add
   resolves and builds cleanly, `make core` clean).

2. frob-core/src/extract.rs: `extract_tree_rust(source: bytes) ->
   (comment_spans, identifiers, tokens)` -- a 3-tuple, not the python
   kernel's 4-tuple, since rust has no python-style string-literal
   docstring facet; rust's `///`/`/** */` doc comments are
   `line_comment`/`block_comment` leaves already, so they land in
   `comment_spans`. This also extended `frob.lang._extract.
   _IDENTIFIER_TYPES` with a `"rust"` entry (`identifier`,
   `type_identifier`, `field_identifier`) -- rust had NO identifier-walk
   counterpart on the Python side before this portion, so the golden-
   parity target this kernel is tested against is new capability added
   in this same change, not a pre-existing one to mirror.

   One real implementation bug the golden-parity check caught and fixed:
   this grammar generation's `line_comment`/`block_comment` nodes are
   NEVER leaves (each carries its own `//`/`/*` delimiter child) --
   unlike python's `comment` node. A leaf-only walk (the approach the
   python kernel uses) silently found ZERO rust comments. Fixed by adding
   `collect_comment_nodes`, a type-match top-down walk mirroring
   `frob.lang._extract._collect_comment_nodes` exactly, used only for
   `comment_spans`; `identifiers`/`tokens` still share the leaf-only walk
   (verified consistent with `_leaf_tokens`'s own literal exclusion
   check, which also only skips a comment when it is itself a leaf).

3. frob-core/src/lib.rs: wired `extract_tree_rust` into the `frob_core`
   `#[pymodule]`.

4. frob-core/frob_core.pyi: typed stub for the new export (never raises,
   verified by `frob check --only ffi_boundary`: 0 errors/warnings).

5. docs/modules/lang.md (Extraction API) + docs/modules/dup.md (frob-core
   kernels) describe the new kernel, the `_IDENTIFIER_TYPES["rust"]`
   addition, and the leaf-vs-type-match comment-walk finding.

6. tests/unit/test_extract_native.py: added `TestExtractTreeRustParity`
   (3 tests) alongside the existing python parity class -- a synthetic
   fixture (struct/impl/field-access/all three comment styles), the
   never-raises contract, and a byte-for-byte parity check against this
   kernel's own source file (`frob-core/src/extract.rs`).

Golden-test proof (ad hoc script, not committed, same precedent as the
python slice): comment_spans/identifiers/tokens compared against
`frob.lang._extract`'s (newly-extended) rust path across this repo's own
`.rs` corpus (frob-core/**, strata-core/**, tests/fixtures/**/*.rs -- 12
files). Result: 0 mismatches across every collection, both before and
after the `--only ffi_boundary`-passing build.

FFI gate compliance: `frob check --only ffi_boundary` -- 0 errors, 0
warnings (whole-file never-raises convention holds; no `# frob:raises`
needed).

Evidence bound (--accepts 0, same acceptance criterion as the python
slice -- this is additional coverage under the same GIVEN/WHEN/THEN, not
a new criterion):
- tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_functions_structs_comments_and_field_access
- tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_unparseable_source_returns_empty_not_a_crash
- tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_this_repos_own_extract_rs_matches_byte_for_byte

Also ran (scoped regression, unchanged behavior confirmed):
`pytest tests/test_lang.py tests/unit/test_lang_primitives.py
tests/unit/test_xref.py -q` -- all pass (the `_IDENTIFIER_TYPES["rust"]`
addition is additive, no existing language's dispatch table entry
changed).

Merge note: warming up this worktree for the series required `git merge
main` (~20 commits behind); one real conflict in design/frob.strata's
testsuite `may "exec" via ...` line (unioned per the dispatch's merge
rule, not either-side-wins). The merge also surfaced 44 tickets present
in BOTH tickets.md and tickets-archive.md (this worktree's stale base
predates their archival on main) -- `run_gates` refused to load the
queue (DuplicateId) until the stale active-side copies were removed in a
separate ledger-hygiene commit (tickets-archive.md untouched,
authoritative). design/frob.strata's testsuite node needed a scope add
(the merge's union touched it) -- `frob ticket scope T-1220 --add
'design/frob.strata'`, followed by `frob ticket sweep T-1220` to refresh
the now-stale pre-work sweep.

Filed: none -- no out-of-scope work discovered this pass beyond the
ledger-hygiene fix already disclosed above (in-scope, tickets.md is
always implicitly in scope per the playbook).

Gates: `frob check --ticket T-1220 --only scope --only prework --only
fmt --only affect_drift --only ffi_boundary` clean (0 errors, 321
warnings, 1 waived -- warnings are the SAME pre-existing scope-breadth
debt from the ticket's own broad `src/frob/lang/**` glob the prior
portion already disclosed, now 321 vs the prior 203 solely because this
portion's own new `_IDENTIFIER_TYPES`/kernel additions widened the doc/
test-edge surface under that same broad glob; not new debt introduced by
narrowing scope). No new waivers added.

Status: leaving T-1220 IN-PROGRESS, not closing -- this is a second
portion, not the whole ticket. Remaining under this same ticket id: cpp/
typescript kernels, and the consumer rewiring (perf/clones/deprecated/
dead_symbols/opaque/sys), the latter explicitly T-1219's job per the
original dispatch brief this ticket's own Done report already noted.

### Changed
```
 design/frob.strata                |   4 +-
 docs/modules/dup.md               |   4 ++
 docs/modules/lang.md              |  33 ++++++++++-
 frob-core/Cargo.lock              |  11 ++++
 frob-core/Cargo.toml              |   1 +
 frob-core/frob_core.pyi           |  14 +++++
 frob-core/src/extract.rs          | 122 ++++++++++++++++++++++++++++++++++++++
 frob-core/src/lib.rs              |   3 +-
 src/frob/lang/_extract.py         |   6 ++
 tests/unit/test_extract_native.py |  82 +++++++++++++++++++++++++
 tickets.md                        |  95 +++++++++++++++++++++++++++--
 11 files changed, 365 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_functions_structs_comments_and_field_access` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_unparseable_source_returns_empty_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_this_repos_own_extract_rs_matches_byte_for_byte` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 2 error(s), 451 warning(s), 769 waived
- error-findings: DUP001@frob-core/src/extract.rs, SELFAUDIT001@design
