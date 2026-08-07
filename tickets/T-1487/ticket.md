---
id: T-1487
title: 'rust: python tree-extraction kernel in frob-core (T-1220 delivered portion
  1)'
state: done
kind: feature
origin: agent
created: '2026-08-03'
priority: high
parent: T-1220
tier: ticket
sprint: null
runs_last: false
scope:
- frob-core/**
- tests/unit/test_extract_native.py
- docs/modules/lang.md
- docs/modules/dup.md
- tests/test_tickets_lease.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_lease.py
  reason: landing requires re-pointing a WIRE001 waiver follow_up= citation that named
    T-1487, since T-1487 is closing without touching that file's fixture
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte
designated_repro_test: null
acceptance:
- text: GIVEN the delivered kernel WHEN the golden-parity tests run THEN they pass
    and ffi_boundary reads 0 errors
  evidence:
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte
threat: null
component: null
---
Leaf carrier for T-1220's first portion: extract_tree_python in frob-core (tree-sitter 0.25 kernel; comment spans, docstring spans, identifiers, token stream behind one non-raising FFI entry), golden-verified byte-for-byte against the Python path across 917 repo files with one documented grammar-generation delta. Consumer rewiring stays T-1219; cpp/rust/ts walkers remain under T-1220.

## Done report

Verification-only pass, no new kernel code required.

Investigation before writing anything (per dispatch instructions,
understanding exactly where T-1220's portion-1 boundary sits): T-1220's
own Done report already records extract_tree_python (the python
tree-extraction kernel) as fully delivered -- 917-file golden parity,
FFI-boundary compliance, docs/modules/lang.md and docs/modules/dup.md
updated in that same change. Confirmed directly against this worktree's
main tip:

- frob-core/src/extract.rs already defines extract_tree_python (line
  207) and frob-core/src/lib.rs already registers it in the frob_core
  pymodule; frob-core/frob_core.pyi already types it.
- tests/unit/test_extract_native.py already contains
  TestExtractTreePythonParity with all four tests this ticket's
  acceptance criterion names.
- docs/modules/lang.md and docs/modules/dup.md already document the
  kernel (Extraction API / frob-core kernels sections).

T-1487's own ledger entry already carried a pre-filled Done report
(evidence, Changed diffstat, Captured claims) despite state=queued --
apparently drafted as a carrier stub when T-1220 was split, but never
actually run through start/land. There is no remaining "next portion"
of python-kernel work inside this ticket's own scope: the whole
scope (frob-core/**, tests/unit/test_extract_native.py,
docs/modules/lang.md, docs/modules/dup.md) as it pertains to the
PYTHON kernel is already satisfied by code on main. Remaining
tree-extraction work (cpp/typescript kernels, consumer rewiring) lives
under the parent T-1220 and T-1219 respectively, outside this ticket's
declared scope -- not something to fold in here.

Re-verified rather than trusted the stale prose:
- `pytest tests/unit/test_extract_native.py -q`: 7 passed (4 python-
  parity + 3 rust-parity, both already-landed kernels).
- `frob check --ticket T-1487 --only ffi_boundary`: 0 errors, 0
  warnings.
- `frob check --ticket T-1487 --only scope --only prework --only fmt
  --only affect_drift`: 0 errors, 154 warnings (SCOPE002 breadth notes
  from the ticket's own broad frob-core/** and docs-file globs pulling
  in unrelated anchors/frob:tests edges elsewhere in those same files --
  same pre-existing debt class T-1220's own Done report already
  disclosed for this scope, not new).
- `frob check --ticket T-1487 --only gates-fast --only gates-native
  --only gates-security`: 0 errors repo-wide across every gate family.

No source change was needed or made; this dispatch's own worktree
commit is only the `ticket start` transition record. Closing T-1487 as
delivered-by-T-1220, with T-1487's own evidence re-verified against
current main rather than merely re-asserted from the stale draft.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 301 warning(s), 724 waived
- error-findings: none (measured, zero errors)
