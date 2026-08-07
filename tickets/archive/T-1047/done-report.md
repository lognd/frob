## Done report

Resumed a dead predecessor session in the same worktree/lease. All code
changes (17-of-25 taxonomy gap closure, commit 18abd5a3) and the
predecessor's own done-report write to tickets.md were already correct
and complete; my work was to verify, land-prep, and land:

- Confirmed 18abd5a3 was already committed and unmodified.
- Ran tests/test_vet.py foreground (238 tests) after a from-scratch
  make core rebuild: all pass, including the 19 flipped
  TestOpaqueIndirectionGate/_fires and _excused_source_invisible tests.
- Ran frob check --ticket T-1047 foreground: no new unwaived errors in
  the 3 touched files (src/frob/vet/_capability_registry.py,
  src/frob/vet/_evasion_coverage.py, tests/test_vet.py); the reported
  DEPR005/COV001/INV006/PERF003/PERF004 baseline errors match the
  predecessor's own captured claims exactly (pre-existing debt, not
  introduced here).
- Committed the predecessor's uncommitted done-report write to
  tickets.md (eb37d4a8).
- Merged main (00e741cc), clean merge, no conflicts.
- Rebuilt natives (make core) and re-ran tests/test_vet.py + frob test
  --base main against the merged tree: both pass.

Disclosed residue (13 rows, not addressed here, follow-up filed and
landed as T-1051, per predecessor's
done-report): python/typescript container-dynamic-key and
computed-member shapes, C/C++ array-index/integer-cast/void*-backcast
shapes need a generalized subscript-or-cast detector the current
needle architecture cannot express safely; rust struct-field,
macro_rules! expansion, cpp pointer-to-member, kotlin destructuring/
default-param/operator-invoke need real alias tracking in the ordinary
resolvers, not a registry entry. T-0339's epic acceptance criterion
therefore does not fully hold yet; a residual ticket names this gap
(follow-up filed and landed as T-1051, itself further followed up by
T-1063 for the remaining structural points-to gaps).

### Changed
```
 src/frob/vet/_capability_registry.py | 213 ++++++++++++++++++++++++++++++++++
 src/frob/vet/_evasion_coverage.py    |  32 ++---
 tests/test_vet.py                    | 218 +++++++++++++++++------------------
 tickets.md                           | 173 +++++++++++++++++++++++++++
 4 files changed, 507 insertions(+), 129 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_c_weak_symbol_override_excused_source_invisible` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_rust_extern_ffi_symbol_excused_source_invisible` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_rust_proc_macro_synthesized_call_excused_source_invisible` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_rust_runtime_vtable_patch_excused_source_invisible` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_combined_registered_total_matches_112_entry_denominator` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_every_litmus_path_resolves_to_a_real_test` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_every_taxonomy_row_has_sufficient_registered_litmus_coverage` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_map_has_no_orphaned_language_category_pairs` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 14 error(s), 1826 warning(s), 362 waived
- error-findings: ARCH001@src/frob/graph/callgraph.py, ARCH001@src/frob/testing/_collect.py, COV001@src/frob/arch/_models.py, COV001@src/frob/gitlog/__init__.py, COV001@src/frob/process/parsers/common.py, COV001@src/frob/render/_color.py, COV001@src/frob/render/_elements.py, DEPR005@tests/system/test_cli_ticket_worktree_root.py, DEPR005@tests/test_gates.py, DEPR005@tests/test_ticket_land.py, DEPR005@tests/test_vet.py, PERF003@src/frob/arch/_cpp_mayraise.py, PERF004@src/frob/arch/_cpp_mayraise.py, PRE001@tickets/T-1047
