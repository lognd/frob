## Done report

Changed:
- src/frob/strata/_selfconform.py::SYS_INTERFACE_CONFORMANCE
- src/frob/strata/_selfconform.py::_interface_conformance_violations
- src/frob/strata/_selfconform.py::_module_public_symbols
- src/frob/strata/_selfconform.py::_module_all_literal
- src/frob/strata/_selfconform.py::_public_names_of_statement
- src/frob/strata/_selfconform.py::_node_real_public_surface
- src/frob/strata/_selfconform.py::_node_attr_values
- src/frob/strata/_selfconform.py::check_self_conformance (wired SYS104 into _collect_sys_violations/_apply_sys_waivers)
- src/frob/strata/__init__.py (re-export SYS_INTERFACE_CONFORMANCE)
- docs/modules/strata.md (SYS104 section)
- tests/unit/strata/test_selfconform.py (TestInterfaceConformance, 5 tests)

SYS104 implements exact interface conformance: a node's declared
`interface=<symbol>` attrs (new opaque `Node.attrs` convention, same
shape as `code=`/`managed`, no `.strata` grammar change) must equal the
real public surface of its `code=`-bound `.py` files (`__all__` if
present, else non-underscore top-level def/class/assignment names).
Fires in both directions: real-but-undeclared, and declared-but-absent.

SCOPE CUT (disclosed): SYS104 only evaluates a node that has already
declared at least one `interface=` attr -- making it mandatory repo-wide
would require adding `interface=` declarations to `design/frob.strata`,
which is outside this ticket's declared scope (`src/frob/strata/**`,
`src/frob/graph/**`, `docs/modules/strata.md`, `tests/unit/strata/**` --
not `design/frob.strata`). This mirrors the T-0667/SYS103 precedent
(`_coverage_totality_scan_prefix`'s own disclosed scope cut). Filed
T-1113 to promote SYS104 to mandatory once `design/frob.strata` can be
edited to carry real `interface=` declarations.

Also landed in this same worktree pass (implementation only lives in
this one file/module, shared by T-0668/T-0669/T-0670): SYS105 (purpose
contract) and SYS106 (binding totality) are ALSO present in this diff
since all three share one `_selfconform.py` module and one
`check_self_conformance` wiring pass -- their own Done reports
(T-0669/T-0670) cite the same file but their OWN new symbols/tests as
Changed, per the series' plan of building all three checks in one pass
before landing each ticket in order. T-0668's evidence below binds only
to the SYS104-specific tests.

Evidence:
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_undeclared_public_symbol_fires
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_declared_but_absent_symbol_fires
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_exact_match_is_silent
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_node_with_no_interface_attr_is_never_checked
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_dunder_all_overrides_name_based_collection

Filed: T-1113 (promote SYS104 to mandatory once design/frob.strata is in scope; follow-up to add CHK-GATE-SYS104 registry cross-reference in docs/design/registry/check-coverage.yaml, mirroring SYS103's own deferred registry gap)

Gates: `uv run frob check --ticket T-0668` clean across prework/lint/
static/gates-native/gates-security/test/coverage/doc*/tickets/registry
(measured directly, chunked per playbook section 3b -- 0 errors in every
group; TestRealGateGreen and TestCoverageTotality::
test_repo_unrestricted_scan_is_clean both still pass zero violations
against the real repo).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_undeclared_public_symbol_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_declared_but_absent_symbol_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_exact_match_is_silent` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_node_with_no_interface_attr_is_never_checked` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_dunder_all_overrides_name_based_collection` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 1 error(s), 1318 warning(s), 429 waived
- error-findings: PRE001@tickets/T-0668
