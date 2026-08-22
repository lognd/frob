## Done report

Verified the seam before splitting. The existing frob:waive LARGE001 on
frob-core/src/lib.rs claimed pyo3's #[pymodule] registration required every
#[pyfunction] visible in crate-root scope -- checked against the crate's own
prior precedent (arch_python.rs/capability_python.rs) and found this false:
extract_tree_*/scan_python_capabilities/py_function_metrics are already
registered in frob_core() via plain `use module::func;` imports from
sibling files, and wrap_pyfunction! only needs the name in scope, not
defined in lib.rs. A function-body scan of the five rungs (R1.5 exact
regions, R3 canonicalization, R4 winnowing/tree-edit-distance, R5
anti-unification/WL-hashing, callgraph/arch-similarity) found ZERO
cross-calls between them -- only `hash_str` is shared (used by R3 and R5),
kept in lib.rs as `pub(crate)`.

Split into frob-core/src/{r3,r4,r5,exact_regions,callgraph}.rs, mirroring
the crate's own arch_python.rs/capability_python.rs extraction pattern:
each rung's #[pyfunction]s and private helpers moved verbatim, registered
in frob_core() via `use` imports exactly like the existing sibling modules.
Renamed the exact_regions() function's IMPORT ALIAS to run_exact_regions
in lib.rs only (module name and fn name collided) -- the #[pyfunction]'s
exposed Python name is unaffected since pyo3 names by the Rust fn
identifier at its definition site (still `exact_regions` in
exact_regions.rs), not by the caller's import alias.

lib.rs shrank from 2297 to 932 lines. That is still over LARGE001's
500-line threshold, so replaced the old (now-inaccurate) waiver with a
corrected one: 834 of the remaining 932 lines are the crate's own
#[cfg(test)] mod tests block (idiomatic Rust, not production bulk); the
rest is module doc, mod/use wiring for six sibling modules, the shared
hash_str helper, and the pymodule registration function -- no further rung
left to extract. Mirrors strata-core/src/lib.rs's own identical
post-split LARGE001 waiver shape.

Verification:
- `uv run frob natives build`: both strata_core and frob_core built
  cleanly after the split.
- `cargo test --release` (frob-core crate, run with PYO3_PYTHON pointed at
  the worktree's .venv and LD_LIBRARY_PATH set to the venv's libpython):
  49 passed, 0 failed -- every pre-existing #[cfg(test)] case, including
  all R3/R4/R5/exact-regions/callgraph cases, now calling into the moved
  functions through the new module boundaries.
- Python-side native-consumer suites re-run against the rebuilt extension:
  tests/test_dup.py, test_dup_cross_lang.py, test_dup_native_rungs.py,
  test_dup_prefilter.py, test_dup_region.py, test_dup_rungs.py,
  test_dup_exhaustiveness.py, test_arch_near_duplicate_native.py --
  96 passed, 0 failed. (tests/test_dup_smart.py::TestFindClones::
  test_core_unavailable_is_honest_err_not_silent_downgrade fails
  identically on main/pre-split, confirmed by running it from the primary
  checkout unmodified -- pre-existing, unrelated to this split.)
- Re-ran the coordinator's mandated arch_gate()+_apply_waivers() check
  against a live build_graph() snapshot: frob-core/src/lib.rs's LARGE001
  is WAIVED (was KEPT/unwaived immediately after the split, before the
  corrected waiver was added -- confirms the directive re-parses and
  re-binds correctly, not just "no exception raised"); none of the five
  new sibling files trip LARGE001 or any other arch rule.

Changed: frob-core/src/lib.rs (rewritten), frob-core/src/r3.rs (new),
  frob-core/src/r4.rs (new), frob-core/src/r5.rs (new),
  frob-core/src/exact_regions.rs (new), frob-core/src/callgraph.rs (new)
Evidence: tests/test_arch_near_duplicate_native.py::test_native_kernel_matches_difflib_over_this_repos_own_arch_tree,
  tests/test_dup_native_rungs.py::TestNativeRungsEnabled::test_enabled_finds_the_r4_gapped_clone,
  tests/test_dup_native_rungs.py::TestNativeRungsEnabled::test_enabled_finds_the_r5_dataflow_clone
Filed: none
Gates: arch_gate()+_apply_waivers() clean for frob-core/** (LARGE001
  waived on lib.rs, no findings on the new sibling files); `cargo test
  --release` 49/49 in frob-core; natives build clean for both crates

### Changed
```
 frob-core/src/callgraph.rs     |  401 +++++++++++
 frob-core/src/exact_regions.rs |  315 +++++++++
 frob-core/src/lib.rs           | 1493 ++--------------------------------------
 frob-core/src/r3.rs            |  111 +++
 frob-core/src/r4.rs            |  354 ++++++++++
 frob-core/src/r5.rs            |  258 +++++++
 tickets/T-2846/ticket.md       |    9 +-
 7 files changed, 1512 insertions(+), 1429 deletions(-)
```

### Evidence
- `tests/test_arch_near_duplicate_native.py::test_native_kernel_matches_difflib_over_this_repos_own_arch_tree` (pytest node id, verified passing when recorded)
- `tests/test_dup_native_rungs.py::TestNativeRungsEnabled::test_enabled_finds_the_r4_gapped_clone` (pytest node id, verified passing when recorded)
- `tests/test_dup_native_rungs.py::TestNativeRungsEnabled::test_enabled_finds_the_r5_dataflow_clone` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 52 error(s), 507 warning(s), 774 waived
- error-findings: AFFECT001@frob-core/src/callgraph.rs, AFFECT001@frob-core/src/exact_regions.rs, AFFECT001@frob-core/src/lib.rs, AFFECT001@frob-core/src/r3.rs, AFFECT001@frob-core/src/r4.rs, AFFECT001@frob-core/src/r5.rs, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@frob-core/src/callgraph.rs, COV001@frob-core/src/exact_regions.rs, COV001@frob-core/src/lib.rs, COV001@frob-core/src/r3.rs, COV001@frob-core/src/r4.rs, COV001@frob-core/src/r5.rs, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC006@docs/modules/dup-sota-survey.md, DOC006@docs/modules/dup.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/dup.md, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@frob-core/src/lib.rs, DRIFT002@tests/test_arch_near_duplicate_native.py, DRIFT002@tests/unit/test_dup_core.py, DSL001@tests/unit/test_coordinator_scripts.py, DUP001@frob-core/src/r5.rs, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2846, REF001@frob-core/src/callgraph.rs, REF001@frob-core/src/exact_regions.rs, REF001@frob-core/src/r3.rs, REF001@frob-core/src/r4.rs, REF001@frob-core/src/r5.rs, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@frob-core/src/exact_regions.rs, TEST001@frob-core/src/lib.rs, TEST001@frob-core/src/r3.rs, TEST001@frob-core/src/r4.rs, TEST001@frob-core/src/r5.rs, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
