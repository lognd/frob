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
