## Done report

**Round 2 correction (reviewer REJECT):** round 1's `exact_regions`/
`merge_diagonals` only compared SA-ADJACENT suffix pairs (`sa[i-1]`,
`sa[i]`), so a block repeated in 3+ documents silently dropped
non-adjacent occurrence pairs (e.g. `(doc0, doc2)` when `doc1`'s matching
suffix sorted between them in the suffix array) -- contradicting the
"finds every maximal region" docstring, and a real correctness bug since
`_region_groups` runs `exact_regions` over every fingerprinted symbol's
tokens in one call. Fixed below; round 1's Done-report content is
superseded by this section.

Changed (round 1 + round 2 fix):
- frob-core/src/lib.rs::flatten_documents
- frob-core/src/lib.rs::build_suffix_array
- frob-core/src/lib.rs::kasai_lcp
- frob-core/src/lib.rs::merge_diagonals
- frob-core/src/lib.rs::lcp_runs (round 2, new) -- finds maximal SA-index
  ranges where every consecutive LCP >= min_len, i.e. every suffix in the
  range shares >= min_len tokens with every OTHER suffix in the same
  range (LCP is a "staircase": the pairwise shared-prefix length between
  any two suffixes in a sorted range is the minimum LCP strictly between
  them, so bounding every adjacent gap bounds every pairwise gap).
- frob-core/src/lib.rs::emit_run_pairs (round 2, new) -- emits every
  occurrence pair within one `lcp_runs` range, not just adjacent ones.
- frob-core/src/lib.rs::exact_regions (round 2, rewritten body) -- now
  calls `lcp_runs`/`emit_run_pairs` instead of only looking at
  `(sa[i-1], sa[i])`.
- src/frob/dup/_core.py::exact_regions
- src/frob/dup/_models.py::DupConfig (new fields: region_kernel_enabled, region_min_tokens)
- src/frob/dup/_pipeline.py::_region_line_span
- src/frob/dup/_pipeline.py::_region_groups
- src/frob/dup/_pipeline.py::find_clones (wired _region_groups into the rung ladder)
- src/frob/gates/__init__.py::_dup_config (now also reads [dup].region_kernel)
- src/frob/gates/__init__.py::dup_gate (threads region_kernel_enabled into DupConfig)
- docs/modules/dup.md (new R1.5 rung row + dedicated section + config block +
  frob-core kernel list + rung-string comment)
- CHANGELOG.md (round 1 put the entry under `[0.4.0]`; round 2 moved it to
  its own `## [0.5.0] - unreleased` heading ABOVE `[0.4.0]` after merging
  main, per reviewer instruction -- no duplicate entries, confirmed via
  `grep -c T-0193 CHANGELOG.md` == 1)
- pyproject.toml (version 0.4.0 -> 0.5.0, REL001's mechanical bump)
- .frob-release.json, uv.lock (mechanical outputs of `frob release stamp` /
  the version bump; re-stamped again after merging main)
- tests/fixtures/dup_region/src/mod_a.py, mod_b.py (new fixture)
- tests/test_dup_region.py (new)
- tests/unit/test_dup_core.py (TestExactRegions + exact_regions cases added
  to test_frob_core_module_registers_exported_kernels and
  test_core_unavailable_path_is_err_not_exception)

Merge: `git merge origin/main` (T-0221 landed on main, `577d084`/`466f5d1`/
`3fb7b76`, vet-lockfile-arg fix -- no public-API changelog entry of its
own, no conflicts with this ticket's files other than tickets.md, which
merged cleanly).

Evidence:
- Cargo (frob-core, `cargo test`, `LD_LIBRARY_PATH` pointed at the
  uv-managed CPython 3.11.15's libpython): **23 passed, 0 failed** -- 10
  total for this ticket, 3 of them the round-2 regression tests the
  reviewer required:
  - `exact_regions_finds_shared_block_inside_different_functions`
  - `exact_regions_below_min_len_reports_nothing`
  - `exact_regions_no_match_across_wholly_different_documents`
  - `exact_regions_does_not_match_across_document_boundary`
  - `exact_regions_merges_overlapping_suffix_pairs_into_one_maximal_region`
  - `exact_regions_empty_input_is_empty_output`
  - `suffix_array_and_kasai_lcp_agree_on_a_hand_checked_case`
  - `exact_regions_three_identical_documents_reports_all_three_pairs`
    (round 2, regression test 1: 3 identical 4-token documents -> asserts
    all of `(0,1)`, `(0,2)`, `(1,2)` are present -- FAILED against the
    round-1 code before the fix, PASSES now)
  - `exact_regions_four_way_shared_block_reports_every_pair` (round 2,
    regression test 2: 4 identical 6-token documents -> asserts all 6
    pairs across `0..4` are present)
  - `exact_regions_mixed_case_two_nested_shared_regions` (round 2,
    regression test 3: 3 documents share a 4-token region A; only 2 of
    those 3 additionally share a 3-token region B immediately following
    A -- asserts region A ties all three pairs AND the doc0/doc1 pair's
    reported length is `>= 7` (proving region B was actually captured,
    not just region A reported twice))
- Pytest, collected via `pytest --collect-only` and then run green (same
  node ids as round 1, all still green post-fix):
  - `tests/unit/test_dup_core.py::TestExactRegions::test_finds_shared_block_inside_different_documents`
  - `tests/unit/test_dup_core.py::TestExactRegions::test_below_min_len_finds_nothing`
  - `tests/unit/test_dup_core.py::TestExactRegions::test_no_shared_tokens_finds_nothing`
  - `tests/unit/test_dup_core.py::test_core_unavailable_path_is_err_not_exception`
  - `tests/unit/test_dup_core.py::test_frob_core_module_registers_exported_kernels`
  - `tests/test_dup_region.py::TestRegionKernelOffByDefault::test_disabled_by_default_finds_no_region_pairs`
  - `tests/test_dup_region.py::TestRegionKernelOffByDefault::test_whole_symbol_rungs_miss_the_partial_clone`
  - `tests/test_dup_region.py::TestRegionKernelFindsPartialClone::test_enabled_finds_shared_region_between_otherwise_different_functions`
  - `tests/test_dup_region.py::TestRegionKernelFindsPartialClone::test_min_len_floor_excludes_too_short_a_region`
  - Full targeted run (post-merge, post-fix): `pytest tests/test_dup_smart.py
    tests/test_dup_rungs.py tests/test_dup_region.py tests/unit/test_dup_core.py
    tests/unit/test_dup.py tests/unit/test_dup_smt.py tests/unit/test_dup_cache.py
    tests/test_gates.py tests/test_vet.py` -- all green (no failures).
- `frob:tests`/`frob:doc` directives bound in-source (non-self-referential,
  `kind="unit"`), including three new ones on the round-2 regression tests;
  `<!-- frob:describes frob-core/src/lib.rs::exact_regions -->` in
  docs/modules/dup.md's kernel-surface anchor block (unchanged, still
  correct -- the fix did not change the function's public signature).

Filed: none. All work landed inside declared (and mid-implementation-widened,
see round 1's note above) scope; no out-of-scope discoveries required a new
ticket.

Gates:
- `frob check --ticket T-0193` (post-merge, post-fix): 0 errors, 55
  warnings, 236 waived -- clean.
- `frob check` (full, unscoped, post-merge, post-fix): **0 errors, 0
  DRIFT002**, 55 warnings, 236 waived, `ruff-format all files formatted`,
  `ty no issues`, `frob-cycle no cycles` -- clean.
- Pre-existing baseline debt (identical to round 1, unchanged by the merge
  or the fix, re-confirmed against the post-merge tree): `TEST006`
  (`.frob/coverage-stamp` missing -- `make coverage` independently fails
  on a full run in this fresh worktree with dozens of unrelated
  `tests/unit/strata/*` failures, a known worktree-natives environment
  artifact per this repo's memory notes), `PERF004` at
  `src/frob/tickets/_land.py:75`, `PERF003` at
  `src/frob/vet/_obfuscation.py:77` -- none of these three files are in
  T-0193's scope and none were touched by this ticket; left un-waived
  in-source (no scoped file to attach a `frob:waive` to) and reported here
  instead. The `TEST005` warnings across `src/frob/strata/**` etc. are the
  downstream effect of the same missing coverage stamp -- pre-existing,
  `TEST005` is WARN-severity here (`severity_overrides`), not blocking
  `frob check`'s pass/fail.

Deletion-filter land check (docs/guides/agent-playbook.md section 9):
`git diff main --diff-filter=D --stat` is empty (checked post-merge,
post-fix, before the final commit) -- no files were reverted or dropped by
this branch relative to `main`.
