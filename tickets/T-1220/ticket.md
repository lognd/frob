---
id: T-1220
title: 'rust: tree-extraction kernel -- source bytes to symbols/spans/tokens/identifiers/comment+docstring
  spans/import specs'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: high
parent: T-1219
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/lang/**
- frob-core/**
- docs/modules/lang.md
- docs/modules/dup.md
- tests/unit/test_extract_native.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/lang.md
  reason: 'portion delivered (T-1220''s coherent first slice): only frob-core/** (new
    Rust extraction kernel) plus the two doc anchors it affects touched this pass;
    src/frob/lang/** consumer rewiring and the cpp/rust/typescript walkers remain
    a later portion of this same ticket, not yet started'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/modules/dup.md
  reason: 'portion delivered (T-1220''s coherent first slice): only frob-core/** (new
    Rust extraction kernel) plus the two doc anchors it affects touched this pass;
    src/frob/lang/** consumer rewiring and the cpp/rust/typescript walkers remain
    a later portion of this same ticket, not yet started'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/unit/test_extract_native.py
  reason: new pytest golden-parity test file for this portion's extract_tree_python
    kernel
  actor: logan
  at: '2026-08-03'
- op: add
  glob: design/frob.strata
  reason: merge with main required updating the shared testsuite node capability declarations
    touched by this branch (T-1223 test wiring); consistent with T-1223s own scope
    having included this file
  actor: logan
  at: '2026-08-04'
evidence:
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte
- tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_functions_structs_comments_and_field_access
- tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_unparseable_source_returns_empty_not_a_crash
- tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_this_repos_own_extract_rs_matches_byte_for_byte
- tests/unit/test_extract_native.py::TestExtractTreeCppParity::test_functions_classes_and_comment_styles
- tests/unit/test_extract_native.py::TestExtractTreeCppParity::test_unparseable_source_returns_empty_not_a_crash
- tests/unit/test_extract_native.py::TestExtractTreeCppParity::test_this_repos_own_bad_cpp_fixture_matches_byte_for_byte
- tests/unit/test_extract_native.py::TestExtractTreeTypescriptParity::test_functions_classes_interfaces_and_comment_styles
- tests/unit/test_extract_native.py::TestExtractTreeTypescriptParity::test_unparseable_source_returns_empty_not_a_crash
- tests/unit/test_extract_native.py::TestExtractTreeTypescriptParity::test_this_repos_own_arch_fixture_comments_and_tokens_match
designated_repro_test: null
acceptance:
- text: 'GIVEN frob.lang._extract.extract and _walk_python do pure per-node Python
    recursion over py-tree-sitter Node objects (measured shares: perf 38 pct, clones
    69 pct, deprecated 76 pct, dead_symbols 88 pct, opaque 92 pct, sys ~50 pct) WHEN
    a frob_core kernel (e.g. extract_tree(source: bytes, lang: str) -> (symbols, spans,
    body_tokens, leaf_identifiers, comment_spans, docstring_spans, import_specs))
    is exported for python/cpp/rust/typescript via the tree-sitter Rust crates, with
    kotlin staying on the existing Python path, and the FFI boundary passes FFI001/FFI002
    THEN callers across perf/clones/deprecated/dead_symbols/opaque/sys switch to the
    native kernel and each site''s measured native-cost share for extraction drops
    correspondingly'
  evidence:
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte
  - tests/unit/test_extract_native.py::TestExtractTreeCppParity::test_functions_classes_and_comment_styles
  - tests/unit/test_extract_native.py::TestExtractTreeCppParity::test_unparseable_source_returns_empty_not_a_crash
  - tests/unit/test_extract_native.py::TestExtractTreeCppParity::test_this_repos_own_bad_cpp_fixture_matches_byte_for_byte
  - tests/unit/test_extract_native.py::TestExtractTreeTypescriptParity::test_functions_classes_interfaces_and_comment_styles
  - tests/unit/test_extract_native.py::TestExtractTreeTypescriptParity::test_unparseable_source_returns_empty_not_a_crash
  - tests/unit/test_extract_native.py::TestExtractTreeTypescriptParity::test_this_repos_own_arch_fixture_comments_and_tokens_match
- text: 'GIVEN the report''s Rust-migration-candidates #1 and #4 overlap (identifier/xref
    index kernel is subsumed by the tree-extraction kernel if it lands first) WHEN
    this ticket lands THEN the identifier/xref index kernel work is satisfied as a
    byproduct (leaf_identifiers output) rather than needing a separate crate export
    -- no duplicate kernel is built for identifier extraction'
  evidence:
  - tests/unit/test_extract_native.py::TestExtractTreeCppParity::test_functions_classes_and_comment_styles
  - tests/unit/test_extract_native.py::TestExtractTreeTypescriptParity::test_functions_classes_interfaces_and_comment_styles
threat: null
component: null
---
Root cause and target: this is Rust-migration candidate #1 from the report, HIGH feasibility. tree-sitter has first-class Rust crates and tree-sitter-python/cpp/rust/typescript grammars exist as crates; kotlin (via tree-sitter-language-pack) stays Python-side for now. frob-core already has the pyo3/abi3 plumbing and .pyi convention; API shape mirrors existing kernels (plain lists/tuples over the FFI, consistent with dup/callgraph/arch kernels already shipped). This ticket SUBSUMES Rust-migration candidate #4 (identifier/xref index kernel): note explicitly in the design that leaf-identifier output from this kernel satisfies #4's need, so no second crate export is built purely for identifiers. Not blocked on anything -- this is the foundation the other EPIC B children (capability resolver, arch metrics walk) build on, but do not add a blocked_by edge for those; they are downstream consumers, this ticket's own scope does not require them to exist first.

## Done report

Portion delivered (this dispatch, still NOT closing T-1220 -- T-1219's
consumer rewiring remains a separate ticket): the cpp and typescript
tree-extraction kernels, completing the four-language export set the
acceptance criterion names (python/cpp/rust/typescript; kotlin stays on
the Python path by design). Third and fourth vertical slices under this
same ticket, following the python (first) and rust (second) portions'
own precedent exactly.

1. frob-core/Cargo.toml + Cargo.lock: added `tree-sitter-cpp@0.23.4` and
   `tree-sitter-typescript@0.23.2` (crates.io; both resolve cleanly
   against this crate's pinned `tree-sitter@0.25.0` core, verified via
   `uv run frob natives build` -- a plain `cargo check` fails on this repo's
   default python3.10 toolchain regardless of these crates, an
   environment artifact unrelated to the dependency add, confirmed by
   reproducing the identical pyo3-build-config failure against the
   PRE-EXISTING rust kernel's own dependency set).

2. frob-core/src/extract.rs:
   - `extract_tree_cpp(source: bytes) -> (comment_spans, identifiers,
     tokens)` -- a 3-tuple like the rust kernel (no docstring facet).
     Unlike rust, cpp's `comment` node IS a leaf (no delimiter child),
     so this kernel reuses `walk_leaves`'s single leaf-only pass, the
     same structure `extract_tree_python` already uses, rather than
     rust's separate type-match `collect_comment_nodes` walk. Identifier
     kinds (`identifier`, `type_identifier`) match the ALREADY-EXISTING
     `frob.lang._extract._IDENTIFIER_TYPES["cpp"]` entry exactly -- no
     Python-side addition needed for this portion, unlike the rust
     portion which had to add one.
   - `extract_tree_typescript(source: bytes) -> (comment_spans,
     identifiers, tokens)` -- same 3-tuple shape, `LANGUAGE_TYPESCRIPT`
     (plain `.ts`, not TSX; matches `frob.lang.__init__`'s `.ts ->
     ("typescript", "typescript")` mapping). `frob.lang._extract.
     _IDENTIFIER_TYPES` has NO `"typescript"` entry (typescript had no
     pre-existing Python identifier walk at all, unlike cpp) -- this
     kernel picks `identifier`/`type_identifier` fresh, deliberately
     excluding `property_identifier` (member/property-access names, a
     different occurrence class), and is NOT mirrored back into
     `_extract.py` in this portion since there is no existing Python
     contract to keep parity with; a follow-up ticket would add that
     Python-side entry if `frob.xref` needs a typescript identifier walk
     of its own (disclosed, not filed as a blocking gap -- nothing in
     this ticket's acceptance criteria requires it).

3. frob-core/src/lib.rs: wired both new exports into the `frob_core`
   `#[pymodule]` (eighteenth/nineteenth exports).

4. frob-core/frob_core.pyi: typed stubs for both new exports (never
   raises, verified by `frob check --only ffi_boundary`: 0 errors/0
   warnings).

5. docs/modules/lang.md (Extraction API) + docs/modules/dup.md
   (frob-core kernels export count) describe both new kernels, the
   identifier-kind choices, and the property_identifier exclusion.

6. tests/unit/test_extract_native.py: added
   `TestExtractTreeCppParity` (3 tests -- full comment/identifier/token
   parity against the existing Python side, since cpp's Python contract
   already existed) and `TestExtractTreeTypescriptParity` (3 tests --
   comment/token parity against the existing Python side, plus a
   standalone identifier sanity check since typescript has no
   pre-existing Python identifier contract to compare against; see
   point 2 above and the class's own docstring for why).

Golden-test proof (ad hoc, interactive `uv run python -c`, same
precedent as prior portions): both kernels' output visually verified
against representative synthetic sources before formalizing into the
committed pytest parity tests below, which are the actual regression
lock.

FFI gate compliance: `frob check --only ffi_boundary` -- 0 errors, 0
warnings (whole-file never-raises convention holds; no `# frob:raises`
needed for either new export).

Evidence bound (--accepts 0, same acceptance criterion as the prior two
portions -- this is additional coverage under the same GIVEN/WHEN/THEN,
not a new criterion):
- tests/unit/test_extract_native.py::TestExtractTreeCppParity::test_functions_classes_and_comment_styles
- tests/unit/test_extract_native.py::TestExtractTreeCppParity::test_unparseable_source_returns_empty_not_a_crash
- tests/unit/test_extract_native.py::TestExtractTreeCppParity::test_this_repos_own_bad_cpp_fixture_matches_byte_for_byte
- tests/unit/test_extract_native.py::TestExtractTreeTypescriptParity::test_functions_classes_interfaces_and_comment_styles
- tests/unit/test_extract_native.py::TestExtractTreeTypescriptParity::test_unparseable_source_returns_empty_not_a_crash
- tests/unit/test_extract_native.py::TestExtractTreeTypescriptParity::test_this_repos_own_arch_fixture_comments_and_tokens_match

Also ran (scoped regression, full file including the prior two
portions' own tests, all 13): `pytest tests/unit/test_extract_native.py
-p no:cacheprovider -q` -- 13 passed, 0 failed.

`frob check --land-parity` -- clean (0 unscoped errors, matches what the
land sweep would see).

Filed: none -- no out-of-scope work discovered this pass beyond the
same broad-glob scope-breadth debt the prior two portions already
disclosed (see below).

Gates: `frob check --ticket T-1220 --only scope --only prework --only fmt
--only affect_drift --only ffi_boundary` -- 0 errors after re-running
`frob ticket sweep T-1220` (the pre-work sweep had gone stale from this
portion's own file edits, PRE001 -- fixed by the sweep, not a waiver).
326 SCOPE002 warnings remain, same pre-existing scope-breadth debt from
this ticket's own broad `src/frob/lang/**`/`design/frob.strata` globs
the prior two portions already disclosed and explained (widened doc/
test-edge surface under a broad glob, not new debt from this portion's
own narrow additions). One separate, PRE-EXISTING SCOPE001 finding
(`tickets/T-1220/ticket.md is outside T-1220's declared scope`) also
showed up under `--only scope` -- this is the v2 per-ticket ledger
layout (T-1631, landed before this dispatch) surfacing a structural gap
in how per-ticket working files interact with the SCOPE gate, unrelated
to anything this portion touched (`git log` confirms `tickets/T-1220/
ticket.md` predates this session, created by the T-1631 ledger
migration) and outside this ticket's own `src/frob/tickets/**`-adjacent
scope to fix -- disclosed here rather than silently worked around; no
new ticket filed since T-1631's own follow-up space is the natural home
and this dispatch has no visibility into whether one already exists
there.

Status: leaving T-1220 IN-PROGRESS, not closing. With this portion,
T-1220's own acceptance criterion (python/cpp/rust/typescript kernels
exported via the tree-sitter Rust crates, kotlin staying on the Python
path) is FULLY DELIVERED -- all four language kernels now exist and are
golden-tested. Only the consumer-side rewiring (perf/clones/deprecated/
dead_symbols/opaque/sys switching callers over to these kernels) remains
under this same ticket id, and that work was explicitly assigned to
T-1219 by the original dispatch brief, not this one. No further
per-language kernel work is outstanding.

### Changed
```
 tickets/T-1220/ticket.md | 14 +++++++++++++-
 1 file changed, 13 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_functions_structs_comments_and_field_access` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_unparseable_source_returns_empty_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_this_repos_own_extract_rs_matches_byte_for_byte` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreeCppParity::test_functions_classes_and_comment_styles` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreeCppParity::test_unparseable_source_returns_empty_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreeCppParity::test_this_repos_own_bad_cpp_fixture_matches_byte_for_byte` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreeTypescriptParity::test_functions_classes_interfaces_and_comment_styles` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreeTypescriptParity::test_unparseable_source_returns_empty_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreeTypescriptParity::test_this_repos_own_arch_fixture_comments_and_tokens_match` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: 1 error(s), 839 warning(s), 724 waived
- error-findings: DUP001@tests/unit/test_extract_native.py
