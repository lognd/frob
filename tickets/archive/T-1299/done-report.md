## Done report

Changed: none (evidence-only close)

Investigation: the ticket body itself states 0 symbols at exactly 0.0%
branch coverage for this package -- all 15 findings are partial-coverage/
module-line, the lower-priority tier, so acceptance[1]'s dead-code
routing criterion is vacuously satisfied (nothing to judge or route).

Ran the package's unit test surface (tests/unit/test_scaffold_managed.py,
tests/unit/test_scaffold_project.py, tests/unit/test_scaffold_stash_guard.py,
tests/unit/test_scaffold_natives_shim.py: 25 tests) standalone:
uv run pytest <those 4 files> -p no:cacheprovider -n0 -q -- all 25 pass.
Sampled three and confirmed each is a real behavioral assertion (not
import-only/filler):
- TestApplyManagedBlocks::test_creates_missing_and_updates_stale: asserts
  real file-content diffs after applying managed hook blocks
- test_render_project_writes_expected_files: asserts real files written
  to disk from a scaffold template render
- TestLegacyCoreCacheDrift::test_legacy_marker_detection_true_for_old_recipe:
  asserts real drift detection against an old Makefile recipe marker

(Additional scaffold-adjacent coverage lives in tests/system/test_scaffold_*.py,
tests/test_worktree_guard.py, tests/test_scaffold_worktree_lease_hook.py,
tests/test_gates.py, tests/unit/test_exports.py, tests/test_ticket_land.py
-- not individually sampled here, listed for completeness.)

`frob check --ticket T-1299 --only test` in this worktree: 0 errors, 6
warnings, none TEST005 (TEST005 not computable here -- no coverage stamp
in this fresh worktree, TEST006 fires instead; playbook sec 6b makes
coverage stamping coordinator-only). Per the T-1297 precedent (sibling
TEST005 ticket, same 0-at-0.0% shape), binding acceptance[0] on the
strength of the ticket's own 0-at-0.0% claim plus this sampled behavioral
verification, not a fresh full-package TEST005 recount (which this
worktree cannot produce).

Evidence:
- tests/unit/test_scaffold_managed.py::TestApplyManagedBlocks::test_creates_missing_and_updates_stale
- tests/unit/test_scaffold_project.py::test_render_project_writes_expected_files
- tests/unit/test_scaffold_natives_shim.py::TestLegacyCoreCacheDrift::test_legacy_marker_detection_true_for_old_recipe

Filed: none

Gates: uv run frob check --ticket T-1299 --only test -- 0 errors, 6
warnings (none TEST005), 3 pre-existing waived warnings unrelated to this
ticket.

### Changed
```
 tickets.md | 204 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++----
 1 file changed, 191 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/unit/test_scaffold_managed.py::TestApplyManagedBlocks::test_creates_missing_and_updates_stale` (pytest node id, verified passing when recorded)
- `tests/unit/test_scaffold_project.py::test_render_project_writes_expected_files` (pytest node id, verified passing when recorded)
- `tests/unit/test_scaffold_natives_shim.py::TestLegacyCoreCacheDrift::test_legacy_marker_detection_true_for_old_recipe` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 6 error(s), 423 warning(s), 684 waived
- error-findings: ARCH001@src/frob/refactor/_scan.py, ARCH001@src/frob/tickets/_land_finalize.py, OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py, RENDER001@src/frob/refactor/_cli.py, SELFAUDIT001@design
