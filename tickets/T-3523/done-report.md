## Done report

Changed:
- src/frob/strata/_selfconform.py (one stale-comment correction)
- src/frob/strata/_selfconform_surface_rules.py (deleted 4 dead functions, corrected the T-1870 comment, dropped now-unused imports)

Measured (grep, this ticket): `_cross_node_referenced_symbols` had
zero callers anywhere in the repo -- only SYS104 (deleted T-1870) ever
consumed it. Its three private helpers
(`_imported_from_spec`/`_src_root_prefixes`/`_resolve_cross_package_
import`) each had exactly one caller, `_cross_node_referenced_symbols`
itself. Deleted all four. `_node_real_public_surface` DOES have a real
caller -- SYS110's `_undeclared_intended_surface_violations` -- so it
was kept; the DEAD001 waiver on it was never present (only
`_cross_node_referenced_symbols` carried one, and that waiver was
removed along with the function).

Verified the T-1870 comment's claim ("SYS106 and SYS108 also depend on
them") was false for both: SYS106
(`_selfconform_binding_rules.py::_binding_totality_violations`) is a
self-contained reachability walk over `resolve_local_import` that
never references either helper; SYS108
(`_duplicate_interface_violations`) only reads `_node_attr_values`.
Chose "delete the dead code" over "build SYS106 to consume it" per the
ticket's own disjunction, since SYS106 already correctly does its job
without these helpers -- wiring them in would be manufactured, not
real, consumption.

Evidence:
- tests/unit/strata/test_selfconform.py::TestBindingTotality::test_laundered_capable_file_fires (SYS106, pytest node id, verified passing)
- tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_duplicate_symbol_fires (SYS108, pytest node id, verified passing)
- tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface::test_real_symbol_outside_declared_set_fires (SYS110/_node_real_public_surface, pytest node id, verified passing)

Filed: none

Gates: `uv run pytest -p no:xdist tests/unit/strata/test_selfconform.py`
clean (71 passed). `uv run frob test --base main` exceeded the 540s
budget and was aborted per the dispatch instructions; relied on the
scoped run instead. `frob check --ticket T-3523 --only affect_drift
--only coverage --only fmt` clean on this ticket's own touched-set
concerns (no AFFECT001/COV002/TODO001/FMT001 against the two touched
files); repo-wide FAIL lines (WAIVE, DRIFT) are pre-existing per the
run's own scope note and target files this ticket never touched.
