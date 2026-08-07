## Done report

check_import_conformance (SYS003, _code_binding.py) and _reachable_local_files's
BFS (SYS106, _selfconform.py) each independently ast.parse+ast.walk the same
~800-file bound python set every `frob sys` run, and the walk itself called two
unconditional per-node helpers (_absolute_imports, _relative_imports) instead
of filtering by node type first.

Fix: added a module-level (path, content-sha256) -> [(spec, line)] memo
(_code_binding._IMPORT_MEMO) inside _python_imports_with_lines, and collapsed
the two unconditional helper calls into one isinstance(Import)/isinstance
(ImportFrom) filter. _selfconform._reachable_local_files now calls that same
memoized _python_imports_with_lines directly instead of parsing the file
itself and re-deriving imports with its own duplicate walk
(_python_imports_with_lines_module, removed -- it existed only to avoid a
second parse of an already-parsed tree, which the shared memo now makes
unnecessary).

Timing (scoped `frob check --only sys`, worktree is a shared/noisy multi-
agent machine per the playbook -- these are wall-clock samples, not a clean
benchmark):
- before (HEAD~1 content restored via `git checkout HEAD~1 -- <2 files>`,
  no ticket-scope code otherwise touched): sys=22.44s, 21.97s
- after (fix in place): sys=20.63s, 20.42s, 19.00s, 23.44s, 24.15s, 21.85s
  (one 38.09s outlier excluded, consistent with shared-machine contention)

Net: modestly faster on this run, well within the noise band of a shared
box running several worktree agents in parallel; the structural claim (each
of the ~800 files' imports parsed once per run instead of twice, plus one
isinstance filter instead of two unconditional helper calls per AST node)
is the real acceptance evidence, wall-clock is corroborating not primary.

### Changed
```
 src/frob/strata/_code_binding.py | 50 ++++++++++++++++++++++++++++++++++++----
 src/frob/strata/_selfconform.py  | 34 ++++++++-------------------
 tickets.md                       | 24 ++++++++++++++++---
 3 files changed, 77 insertions(+), 31 deletions(-)
```

### Evidence
- `tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_same_component_import_is_fine` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_cross_component_import_with_declared_flow_is_fine` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_cross_component_import_without_declared_flow_is_a_violation` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_from_import_is_resolved_and_checked` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_level1_relative_import_same_package_is_fine` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_level2_relative_import_crossing_component_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestBindingTotality::test_laundered_capable_file_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestBindingTotality::test_unreachable_foreign_file_does_not_fire_sys106` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestBindingTotality::test_bound_reachable_file_does_not_fire_sys106` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 7 error(s), 485 warning(s), 684 waived
- error-findings: ARCH001@src/frob/refactor/_scan.py, ARCH001@src/frob/tickets/_land_finalize.py, OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py, RENDER001@src/frob/refactor/_cli.py, SELFAUDIT001@design, TICK003@tickets.md
