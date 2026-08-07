## Done report

Session scope (effort-budgeted slice of a 53-file LARGE001 residue):
read the full LARGE001 list, prioritised the largest/most-editable
remaining vet/ file (src/frob/vet/_capability_typescript.py, 1275 lines,
the largest per-language capability resolver left after T-1458 already
split _capability.py by language into _capability_c.py/_capability_
python.py/_capability_typescript.py/_capability_scan.py).

Read the full symbol list and found a real pipeline-phase seam already
implicit in the file's own commentary (T-0377 lineage): "build the
import/require/dynamic-import binding table + scope-shadowing walk"
(_TS_SCOPE_TYPES through _ts_import_table) is a distinct, independently
readable phase from "resolve subscript/member/identifier expressions
and the local alias table against that binding table, down to the
public _ts_binding_capabilities/_ts_binding_operations/_ts_resolved_
candidates entry points" (_ts_static_template_text through the file's
tail). Split verbatim on that boundary into
src/frob/vet/_capability_typescript_bindtable.py (593 lines: binding-
table construction) and the remaining src/frob/vet/_capability_
typescript.py (708 lines: expression resolution + entry points). Both
clear the 800-line LARGE001 threshold. The dispatcher
(src/frob/vet/_capability.py) only ever imported the 3 entry-point
names, all of which stayed in the file it already imports from, so its
import block needed no change. Ran `ruff check --fix` to resolve the
import-sort/unused-import fallout from the split, then hand-verified
the two remaining F821s (functions used across the new boundary) by
adding them to the explicit import list.

Deliberately did NOT split by force to hit a specific count across the
other 52 files this session -- most of the remainder needs its own
from-scratch seam read (strata/_selfconform.py at 1911 lines,
tickets/_land.py at 2688 lines, tickets/_store.py at 2260 lines,
tickets/_models.py at 2063 lines, gates/__init__.py at 7627 lines, the
two Rust natives files) that this session's time budget did not reach.
Not splitting those is a disclosed cut, not a silent one -- T-1420
stays open with 52 unwaived files remaining (one file resolved this
session, from 54 unwaived at session start to 53).

Measurement: unscoped `frob check --only archgate` before this
session's change: gate:LARGE 54 warnings (53 unwaived + 1 waived).
After: gate:LARGE 53 warnings (52 unwaived + 1 waived) -- 1 file
cleared. gate:ARCH stayed 0 errors/0 warnings/61 waived throughout
(unaffected by this split). `pytest tests/test_vet.py` -p
no:cacheprovider -q: 443 passed, 0 failed (SUITE-RESULT line read
directly, not piped).

### Changed
```
 src/frob/vet/_capability_typescript.py           | 597 +----------------------
 src/frob/vet/_capability_typescript_bindtable.py | 593 ++++++++++++++++++++++
 tickets.md                                       |   3 +-
 3 files changed, 609 insertions(+), 584 deletions(-)
```

### Evidence
- `tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_unexcused_empty_cells` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestMatrixExhaustiveness::test_matrix_covers_every_kind_and_language` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestMatrixExhaustiveness::test_every_operation_kind_and_language_registered` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestValidateRegistryKinds::test_known_kinds_pass` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_covers_every_needle_table_module` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_survives_a_foreign_install_copy` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_unwired_private_function_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_called_private_helper_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_new_public_function_with_no_caller_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_relocated_symbol_via_file_split_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSysGate::test_sys001_dangling` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSysGate::test_doc003_proved_claim_passes` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_compliance_violation` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_clean_model_no_violations` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestRenumberOneV2::test_git_mv_renames_directory_and_rewrites_id_field` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestRenumberOneV2::test_sibling_ticket_prose_citation_rewritten` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestRenumberOneV2::test_dry_run_mutates_nothing` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestRenumberOneV2::test_target_id_already_exists_is_duplicate_id` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestRenumberOneV2::test_unknown_old_id_is_not_found` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 19 passed (from 19 evidence id(s))
- gates: 0 error(s), 1791 warning(s), 797 waived
- error-findings: none (measured, zero errors)
