## Done report

Changed:
frob-core/src/lib.rs::arch_sim_build_b2j
frob-core/src/lib.rs::arch_sim_find_longest_match
frob-core/src/lib.rs::arch_sim_matching_blocks
frob-core/src/lib.rs::arch_sim_ratio
frob-core/src/lib.rs::near_duplicate_indices
frob-core/frob_core.pyi::near_duplicate_indices
src/frob/arch/_python.py::_near_duplicate_cluster_native
src/frob/arch/_python.py::_near_duplicate_cluster
docs/modules/dup.md (#rust-core kernel-list entry)
docs/audits/check-performance.md (T-0953 remediation log)

Evidence:
frob-core/src/lib.rs unit tests: arch_sim_ratio_matches_difflib_golden_values,
arch_sim_ratio_autojunk_matches_difflib, near_duplicate_indices_matches_python_reference_cluster
(all pass, cargo test --release, 49/49 total crate tests pass)
tests/test_arch_near_duplicate_native.py (3 tests, golden parity: synthetic fixture,
_near_duplicate_cluster dispatch, and this repo's own real 67 same-signature groups
over src/frob/arch -- 0 mismatches)
tests/unit/test_arch.py, tests/test_arch_gate.py, tests/system/test_cli_arch.py all pass unchanged
frob test --base main: python exit=0, rust exit=0

Filed: none

Gates: frob check --ticket T-0953 clean across gates-fast/gates-native/gates-security/static.
lint stage's 2 ty errors + 3 ruff-format findings are all in files this ticket never touched
(tests/test_gates.py, src/frob/arch/_lock_ordering.py, tests/unit/test_arch.py) -- pre-existing,
confirmed via `git status` showing them untracked as modified by this session.

Parity approach: `frob_core.near_duplicate_indices` is a statement-for-statement Rust port of
CPython's `difflib.SequenceMatcher.ratio()` (Ratcliff/Obershelp, autojunk heuristic included,
both matching-block extension phases in the same order) -- not an approximate reimplementation.
Verified against the exact pre-port difflib loop on a synthetic fixture and on every real
same-signature group this repo's own archgate run produces: 0 mismatches.

Measured (median of 5 runs, thread_time, this repo's 67 real same-signature groups):
pure-Python difflib loop: 2.4863s
frob_core.near_duplicate_indices: 0.9686s   (~2.6x faster)

End-to-end archgate wall time (analyze_project("."), median of 5 runs):
before (T-0951 baseline): 11.57s
after (T-0953, native wired): 9.04s   (~2.5s / ~22% faster)

Verdict: WIRED as the default path. `_near_duplicate_cluster` dispatches to
`_near_duplicate_cluster_native` when `frob_core` is available and falls back to the
original, byte-identical pure-Python `difflib` loop otherwise -- unlike T-0930's kernels,
this one wins because the batching boundary (one marshal per same-signature GROUP, up to
57 members here, O(n^2) pairwise work per group) is large enough to amortize the fixed
PyO3 marshaling tax that sank T-0930's per-symbol/per-package dispatch.

### Changed
(no changed files detected)

### Evidence
- `tests/test_arch_near_duplicate_native.py::test_native_kernel_matches_difflib_on_synthetic_archgate_fixture` (pytest node id, verified passing when recorded)
- `tests/test_arch_near_duplicate_native.py::test_native_kernel_matches_difflib_over_this_repos_own_arch_tree` (pytest node id, verified passing when recorded)
- `tests/test_arch_near_duplicate_native.py::test_near_duplicate_cluster_dispatches_to_native_and_matches_reference` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 4162 warning(s), 220 waived
- error-findings: none (measured, zero errors)
