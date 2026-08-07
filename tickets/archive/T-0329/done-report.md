## Done report

Epic verification close (re-applied: the first close was wiped uncommitted by a concurrent land preflight reset -- the close verb lacks T-1130 auto-commit, follow-up filed): all four children (normalized model, TS adapter T-0681, rust adapter, kotlin grammar+adapter) landed and archived; verified live on main 2026-07-29: src/frob/arch/ contains _kotlin.py/_rust.py/_typescript.py alongside _python.py/_cpp.py on the normalized-model protocol, the kotlin grammar resolves via tree-sitter-language-pack (pyproject T-0613 note), and the full tests/unit/test_arch.py suite (143 tests incl 63 cross-language adapter/normalized-model cases) passes on current main. Acceptance holds: checks written once against the normalized model fire across python+ts+rust+kotlin; python/cpp checks were refactored onto the model with no regression per the archived children's own evidence. No code change in this close.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_arch.py::TestNormalizedModel::test_hand_built_python_snippet_shape` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSharedCheckOnPythonAndTypeScript::test_long_complex_function_flags_identically_across_languages` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSharedCheckOnPythonAndRust::test_long_complex_function_flags_identically_across_languages` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSharedCheckOnPythonAndKotlin::test_long_complex_function_flags_identically_across_languages` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
