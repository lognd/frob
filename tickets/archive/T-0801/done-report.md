## Done report

Implemented the combined-vs-split guard-shape normalization axis in
frob.dup._pipeline: `_abstract_if_conditions` (abstracts `if`/`elif`
condition tokens to `$cond`), `_abstract_guard_exit_bodies` (collapses a
guard clause's body down to a bare `return $ERROR_EXIT_MARKER` when that
is its nearest unconditional tail, dropping branch-specific side-effect
content such as a per-branch log message), and
`_collapse_duplicate_guard_chains` (folds adjacent identical guard-exit
blocks into one). Wired via a new shared `_normalize_guard_shape` helper
into both call sites that needed it: `_r2_normalize` (R2+ hash/fingerprint
path) and `_r4_alignment` (the R4 near-miss floor, which is the actual
gate the real motivating pair was sinking under -- `_r4_alignment` calls
`_normalize_error_channel` directly and does not go through
`_r2_normalize`, so both call sites needed the new pass independently).

Verified with a standalone probe script (not part of the test suite) that
the REAL current-source pair (frob.tickets._leases._git_common_dir vs
frob.gates._exclude_hazard._git_common_dir) already registers as a
duplicate at rung r2, similarity 0.95 today -- this pair converged to a
single-if shape as a side effect of T-0784's seam unification (both are
now thin wrappers delegating to frob.gitio.git_common_dir), independent of
this ticket's own normalization work. The historically-described 0.444
non-registering shape (combined-if vs two-separate-ifs-with-different-log-
messages) no longer exists in the real functions, but I still implemented
the general normalization capability per the ticket's Plan/Scope-sketch,
verified it against a synthetic fixture recreating that exact historical
shape (TestConditionalShapeDupPairing), and added
TestRealGitCommonDirPairRegisters as a live regression lock reading the
actual real source files directly (not embedded literal text) so a future
edit that reintroduces the split-guard divergence is caught.

Hit and fixed a real bug in my own first draft along the way: my initial
guard-collapsing logic bounded a guard block's span by "next `if`
occurrence", which incorrectly absorbed trailing sibling code into the
last guard's own span (this flat token stream carries no indentation/
block-boundary info). Fixed by bounding a guard's span at its own nearest
`return $ERROR_EXIT_MARKER` tail instead, and re-scanning normally after
it. Also hit and fixed a real regression: abstracting only `if` (not
`elif`) conditions broke TestR3ElifDesugar (the elif-vs-nested-if/else R3
equivalence, T-0447) whenever the two sides' conditions differ in
spelling, since a manually-nested `if`'s condition got abstracted while
`elif`'s did not before r3_canonicalize's later elif->else:if desugar.
Fixed by abstracting `elif` conditions identically to `if`.

Measured:
- tests/test_dup.py: 25 passed (was 17; added 8 new tests: 5 unit tests on
  the three new functions in TestConditionalShapeNormalization, 1 positive
  end-to-end synthetic-historical-shape test
  (TestConditionalShapeDupPairing), 1 real-source regression lock
  (TestRealGitCommonDirPairRegisters), 1 new negative control
  (TestErrorChannelNormalizationDoesNotOverFire::
  test_genuinely_different_guard_bodies_do_not_falsely_pair)).
- tests/test_dup_cross_lang.py, test_dup_exhaustiveness.py,
  test_dup_inline.py, test_dup_prefilter.py, test_dup_r5_multilang.py,
  test_dup_region.py, test_dup_rungs.py, test_dup_smart.py: 86 passed (no
  regressions in the wider dup suite).
- ruff check (both `uv run ruff` and PATH `ruff`): clean on
  src/frob/dup/_pipeline.py and tests/test_dup.py.
- `frob check --only lint --ticket T-0801`: PASS, 0 errors, 0 warnings.
- `frob check --only static --ticket T-0801`: PASS, 0 errors (pre-existing
  unrelated warnings only, e.g. frob-exports gaps in other packages).
- `frob check --only gates-fast --ticket T-0801`: PASS, 0 errors, 919
  warnings (162 waived, all pre-existing).
- `frob check --only gates-native --ticket T-0801`: PASS, 0 errors, 932
  warnings (44 waived, all pre-existing).
- `frob check --only gates-security --ticket T-0801`: PASS, 0 errors, 934
  warnings (18 waived, all pre-existing).

Sibling: T-0800 describes the same real motivating pair and the same
normalization axis (its Plan sketch speculated a frob_core/Rust-level
desugar might be needed; that speculation predated confirming the fix is
achievable purely in Python). This work fully resolves T-0800's
description too -- no separate frob-core change was needed. T-0800's own
Done report says so plainly and defers close-vs-drop to the coordinator,
per dispatch instructions.

No out-of-scope discoveries filed; no drafts opened.

### Changed
```
 src/frob/dup/_pipeline.py | 239 +++++++++++++++++++++++++++++++++++++-
 tests/test_dup.py         | 284 ++++++++++++++++++++++++++++++++++++++++++++++
 tickets.md                | 101 ++++++++++++++++-
 3 files changed, 617 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_dup.py::TestRealGitCommonDirPairRegisters::test_real_git_common_dir_pair_registers_as_a_duplicate_group` (pytest node id, verified passing when recorded)
- `tests/test_dup.py::TestConditionalShapeDupPairing::test_combined_vs_split_guard_git_common_dir_registers_as_a_duplicate_group` (pytest node id, verified passing when recorded)
- `tests/test_dup.py::TestConditionalShapeNormalization::test_abstracts_if_and_elif_conditions_uniformly` (pytest node id, verified passing when recorded)
- `tests/test_dup.py::TestErrorChannelNormalizationDoesNotOverFire::test_genuinely_different_guard_bodies_do_not_falsely_pair` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
