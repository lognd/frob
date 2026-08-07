## Done report

RENDER001 x4 in src/frob/refactor/_cli.py: run_refactor_command's success-path
report lines used bare print() to stdout, bypassing frob.render
(INV-RENDER-SOLE-STDOUT). Routed through Renderer.for_stream(sys.stdout) +
renderer.line(...), matching the convention every other frob.app.*_runner
module already uses (e.g. src/frob/app/vet_runner.py). The refusal path's
print(..., file=sys.stderr) is untouched (RENDER001 exempts stderr writes).

ARCH001 in src/frob/refactor/_scan.py: _handle_from_import was 63/60 lines.
Extracted the alias-collision-rewrite branch (auto-alias on a
destination-name collision) into a new private helper,
_alias_collision_rewrite, so _handle_from_import now just dispatches
between the collision and plain-rebuild branches per alias.

COV007 in src/frob/refactor/_apply.py: the frob:doc/frob:tests anchor sat
on the private _find_overlapping_ops helper. Moved it onto its public
caller, apply_plan (which already carried its own frob:doc anchor pointing
at the same doc section) -- merged the frob:tests edge in rather than
duplicating the frob:doc line.

COV001 in design/frob.strata:2125: the refactor node was public
(interface= attrs) with no frob:doc edge. Added
`frob:doc docs/commands/refactor.md#public-api` above the node, pointing
at the section of the doc T-1197 already wrote describing this package's
public API.

Fixing RENDER001 touched run_refactor_command's body, which trips
AFFECT001 (its own affects()-closure doc, docs/commands/refactor.md#cli /
#public-api-reference, was not touched in the diff). docs/commands/
refactor.md was not in T-1336's original scope, so widened scope via
`frob ticket scope T-1336 --add docs/commands/refactor.md` (reason
recorded in the ticket's scope_changes audit trail) and added a short
note under "CLI wiring status" describing the Renderer migration.

No new residue tickets needed: the two ARCH001 findings that remain after
this change (src/frob/gates/_debt_deprecated.py::_depr005_violations,
src/frob/tickets/_land_finalize.py::_land_squash_apply) are pre-existing,
outside src/frob/refactor/**, and already tracked -- T-1338 (filed before
this ticket started, confirmed on main at commit 1932da10) covers the
_debt_deprecated.py ARCH001/PERF003/PERF008 cluster.

### Changed
```
 design/frob.strata          |  1 +
 docs/commands/refactor.md   |  6 ++++
 src/frob/refactor/_apply.py |  3 +-
 src/frob/refactor/_cli.py   | 10 ++++---
 src/frob/refactor/_scan.py  | 67 +++++++++++++++++++++++++++++----------------
 tickets.md                  | 30 ++++++++++++++++----
 6 files changed, 83 insertions(+), 34 deletions(-)
```

### Evidence
- `tests/test_refactor.py::TestCli::test_add_refactor_parser_registers_move_and_rename` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestCli::test_run_refactor_command_reports_refusal_exit_code` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestScanReferences::test_finds_from_import_call_site` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestScanReferences::test_auto_alias_on_call_site_name_collision` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestApplyPlan::test_overlapping_ops_refuse_before_write` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestApplyPlan::test_apply_then_rollback_restores_tree` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 6 error(s), 509 warning(s), 686 waived
- error-findings: ARCH001@src/frob/gates/_debt_deprecated.py, ARCH001@src/frob/tickets/_land_finalize.py, OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py, PERF003@src/frob/gates/_debt_deprecated.py, TICK003@tickets.md
