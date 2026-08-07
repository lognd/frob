## Done report

Chose OPTION 3 (narrow SYS104 to symbols actually referenced across node
boundaries), the option the ticket itself flagged as most principled,
over option 1 (exempt test-tree nodes) or option 2 (an interface_exempt
escape hatch). Reasoning: option 1/2 special-case tests specifically and
leave the underlying problem -- "interface=" declaring the WHOLE real
public surface rather than a genuine contract -- untouched for every
other node; option 3 fixes the general problem, and the ticket's own
prediction that it "would shrink every node's list, not just testsuite's"
held (see numbers below).

Implementation: `_cross_node_referenced_symbols` (src/frob/strata/
_selfconform.py) walks every bound .py file's `from <module> import
<name>` statements, resolves `<module>` in-repo, and -- when the target
file is owned by a DIFFERENT node than the importer -- records `<name>`
as required for the target's node. SYS104's required surface becomes
`real_public_surface & cross_node_referenced`, computed once per
check/sync run and threaded through both `_interface_conformance_
violations` (the gate) and `_sync_interface.py`'s writer (so gate and
writer agree on what "required" means -- otherwise every sync run would
immediately re-drift against the gate it's meant to satisfy).

A real infrastructure gap surfaced immediately on the whole-repo pass:
`resolve_local_import`'s python branch resolves a dotted spec by literal
`spec.replace(".", "/")` against `root`, with no src-layout awareness.
A RELATIVE import's dotted prefix is derived from the importing file's
own on-disk position (already carries the `src.` segment via
`_code_binding.py`'s `_dotted`), so it resolves fine -- but an ABSOLUTE
cross-package import (`from frob.excludes import x`, this repo's
dominant CROSS-NODE shape) never resolved against the real repo root,
confirmed directly:
`resolve_local_import("frob.excludes", ..., root=<repo root>)` returns
None even though `src/frob/excludes.py` exists. SYS106's own
`_reachable_local_files` has silently eaten this gap for a while --
invisible there since an unreached file just stays unflagged -- but my
narrowing cannot afford to silently drop nearly every real cross-node
reference. `_resolve_cross_package_import`/`_src_root_prefixes` derive
the missing prefix from the bound file layout itself (no hardcoded
"src") and retry.

Applied via `frob sys sync-interface` (no --check) after the code
change: design/frob.strata 2363 -> 1798 lines. testsuite's own
interface collapsed to `[]` (0 symbols, from 5277) -- confirming nothing
in the repo ever imports a test by name. Total declared interface
symbols across the WHOLE file: ~9000 -> 1457 (smaller than the ticket's
own back-of-envelope ~3700 estimate for "everything except testsuite",
because the general narrowing also trimmed other nodes' previously
over-declared surface, not only testsuite's -- exactly the effect the
ticket predicted and preferred). Re-ran --check immediately after: 0
drift (idempotent). Confirmed the file still parses via
frob.lang.parse_file. `frob check --only sys --ticket T-1625`: 0 errors
-- the full-repo `check_self_conformance` integration test
(TestRealGateGreen.test_repo_design_and_declarations_are_self_conformant)
passes with zero violations against the regenerated file.

Every existing TestInterfaceConformance/TestSyncInterfaceReport unit
test that asserted the OLD "declared == full real surface" semantics
was updated to add an explicit cross-node consumer file/node -- the
new semantics require one before a symbol is expected to be declared
at all; each test's docstring/comment now says why.

### Changed
```
 design/frob.strata                       | 1857 ++++--------------------------
 src/frob/strata/__init__.py              |    2 +
 src/frob/strata/_selfconform.py          |  295 ++++-
 src/frob/strata/_sync_interface.py       |  187 +--
 tests/unit/strata/test_selfconform.py    |  170 ++-
 tests/unit/strata/test_sync_interface.py |  159 ++-
 tickets.md                               |  237 +++-
 7 files changed, 1146 insertions(+), 1761 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_undeclared_public_symbol_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_declared_but_absent_symbol_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_exact_match_is_silent` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_node_with_no_interface_attr_is_never_checked` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_dunder_all_overrides_name_based_collection` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_no_drift_reports_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_addition_and_removal_detected` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_duplicate_blocks_collapsed_to_one` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 0 error(s), 301 warning(s), 870 waived
- error-findings: none (measured, zero errors)
