## Done report

Changed:
- src/frob/vet/_capability.py::_shadowing_scope (new -- replaces the bool-only
  `_is_shadowed` internals; returns the binding SCOPE NODE so callers can look
  up a dangerous alias recorded for that exact binding)
- src/frob/vet/_capability.py::_is_shadowed (kept as a thin bool wrapper over
  `_shadowing_scope`, unchanged external behavior)
- src/frob/vet/_capability.py::_resolve_py_expr (new optional `alias_table`
  param -- when an identifier is locally shadowed, consults the alias table
  for that binding scope instead of unconditionally giving up)
- src/frob/vet/_capability.py::_enclosing_py_scope (new -- nearest
  function/class/module ancestor of a node)
- src/frob/vet/_capability.py::_build_py_alias_table (new -- the T-0337
  scope-local copy-propagation pass: single document-order tree walk
  recording `scope.id -> {name: resolved_dangerous_target}` for plain-
  identifier assignment targets whose RHS resolves via the import table, a
  dangerous attribute chain, or an already-recorded alias in the same
  walk -- transitive chains work because document order visits an earlier
  alias before a later statement copies it; sticky/non-flow-sensitive by
  design, `setdefault` keeps the first dangerous resolution so a later
  benign rebind of the same name does not clear the flag (the documented
  may-analysis over-approximation))
- src/frob/vet/_capability.py::_collect_py_candidates,
  _python_resolved_candidates (threaded the new `alias_table` through)

Root cause of an early false negative during implementation: the original
scope-cache/shadow-check keyed scopes by Python `id(node)` on tree-sitter
Node WRAPPER objects, which are re-allocated per traversal (`.parent` does
not return the same wrapper object twice) -- so a scope recorded during the
alias-table build pass never matched the same scope looked up later during
call-site resolution, and every rebind silently resolved to nothing. Fixed
by keying on the tree-sitter node's own stable `.id` property instead of
Python object identity (`_shadowing_scope`/`_build_py_alias_table` both use
`cur.id`/`scope.id` now, not `id(cur)`).

Evidence: tests/test_vet.py::TestCapabilityScanLocalRebindResolution
- test_single_rebind_detected
- test_chained_rebind_detected
- test_attribute_rebind_detected
- test_benign_rebind_not_detected
- test_parameter_shadow_still_not_detected
- test_dangerous_then_benign_rebind_stays_detected
All 6 passed (`uv run pytest tests/test_vet.py::TestCapabilityScanLocalRebindResolution -v` -> 6 passed in 2.78s).
Full `tests/test_vet.py` (145 tests) green. Repo-wide `make coverage`
(`uv run pytest --cov=src/frob --cov-branch --cov-report=xml -q`) passed
2986+ tests, exit 0, coverage stamped (`frob check --stamp-coverage` ->
409 files, source_sha=7c231ae5).

Filed: none -- no out-of-scope work discovered.

Gates: `uv run frob check --ticket T-0337` clean: 0 errors, 48 warnings (all
pre-existing repo-wide, 25 waived with reasons, none newly introduced by
this change). `ruff check`/`ruff format --check` clean under both the
project-pinned `uv run ruff` and the PATH `ruff`. `frob test --base main`
selected and ran the touched-set (`tests/system/test_cli_vet.py::
TestHookMode::test_old_package_passes`, `tests/test_vet.py`) -> exit 0.
`git diff main --diff-filter=D --stat` empty (no unintended deletions).

Docs: docs/modules/vet.md is in this ticket's scope but was not edited --
it documents `scan_file_capabilities`'s public contract only (bare
capability-kind set), which this change does not alter; the T-0328 binding
resolver's internal mechanics were never separately documented there
either, and `frob check` reports zero doc-drift/doc-coverage violations
for this change (docanchor/doclink/coverage gates all pass).
