## Done report

Rework in response to reviewer rejection (all five findings fixed, two
were BLOCKING):

1. (BLOCKING) apply_plan now detects overlapping/duplicate line ranges
   across RewriteOps targeting the same file and refuses with
   Err(RefactorError.OverlappingRewrites) before any write --
   _find_overlapping_ops in _apply.py. scan_references applies the same
   discipline one phase earlier for the semicolon-joined case:
   _shares_line_with_sibling_statement detects when a from-import shares
   its physical line with another statement and reports it via
   `unresolved` instead of emitting a destructive whole-span rewrite op.
   New tests: TestApplyPlan.test_overlapping_ops_refuse_before_write,
   TestScanReferences.test_semicolon_joined_from_import_refuses_rewrite.

2. verify_check_delta now invokes `sys.executable -m frob check --delta`
   instead of a bare `frob` on PATH (agent-playbook.md sec 2 -- bare frob
   can be a stale global install). New test:
   TestVerify.test_check_delta_uses_current_interpreter (monkeypatches
   guarded_subprocess_run and asserts the exact argv prefix).

3. (BLOCKING) verify_import_resolution now performs real import-graph
   resolution: for every touched file's absolute `from <local module>
   import <name>` statement, it confirms `<name>` is actually defined at
   that module's top level (function/class/assignment/re-exported
   import), not merely that the file parses. Scope is disclosed
   explicitly in the function's own docstring and docs/commands/
   refactor.md: repo-owned modules under src/ only, absolute imports
   only -- third-party/stdlib and relative imports are out of v1's
   static-AST reach and are never flagged. `repo_root=None` preserves the
   old syntax-only fallback for a caller with no enclosing repo, and the
   VerifyOutcome.detail string always discloses which mode ran (never
   silently claims full resolution when it didn't happen). Also fixed
   _handle_import's attribute-style-reference matcher, which only ever
   matched a single-Name hop and so silently missed every dotted,
   non-aliased `import pkg.mod` usage (`pkg.mod.greet()` is
   Attribute(Attribute(Name,'mod'),'greet'), not Attribute(Name,'greet'))
   -- it now walks the full dotted attribute chain. New tests:
   TestVerify.test_import_resolution_catches_dangling_reference,
   TestVerify.test_import_resolution_local_import_resolves,
   TestScanReferences.test_unresolved_attribute_style_reference_surfaces.

4. Added a real test for apply_plan's OSError failure path
   (monkeypatched Path.write_text) and run_refactor's pre-commit
   reset-and-clean recovery, asserting the tree is restored to the
   pre-transaction sha with an empty `git status --porcelain`. New
   tests: TestApplyPlan.test_apply_failed_on_write_error_reports_apply_failed,
   TestRunRefactor.test_apply_failure_recovers_clean_precommit_tree.

5. Added coverage for the unresolved attribute-style-reference path
   (`import old.module` + `old.module.qualname(...)` usage), asserting
   `unresolved` populates with the exact dotted reference and file.
   TestScanReferences.test_unresolved_attribute_style_reference_surfaces
   (also required the _handle_import dotted-chain fix under finding 3 to
   actually pass, not just exist).

Also: run_refactor now propagates apply_plan's real error value
(OverlappingRewrites vs. ApplyFailed) instead of collapsing every
apply-phase failure into ApplyFailed. docs/commands/refactor.md updated
to describe all of the above (Apply/Verify sections, per-symbol
reference blocks) rather than leaving the stale "a stand-in" prose.

tests/test_refactor.py: 32 tests total (11 new), all pass:
`uv run pytest tests/test_refactor.py -p no:cacheprovider -q` -> 32
passed. `uv run ruff check src/frob/refactor/ tests/test_refactor.py`
clean under both the PATH ruff and `uv run ruff` (project-pinned).
`uv run frob check --ticket T-1197 --budget 100` shows no new
src/frob/refactor or tests/test_refactor.py findings beyond the
already-waived TEST003 (no CLI integration entrypoint, pre-existing,
out of this ticket's scope per its declared scope excluding
src/frob/_cli_parsers/** and src/frob/__main__.py).

### Changed
```
 docs/commands/refactor.md         | 283 ++++++++++++++
 src/frob/refactor/__init__.py     |  63 +++
 src/frob/refactor/_apply.py       | 178 +++++++++
 src/frob/refactor/_cli.py         | 113 ++++++
 src/frob/refactor/_models.py      | 211 ++++++++++
 src/frob/refactor/_resolve.py     | 108 +++++
 src/frob/refactor/_scan.py        | 377 ++++++++++++++++++
 src/frob/refactor/_transaction.py | 315 +++++++++++++++
 src/frob/refactor/_verify.py      | 255 ++++++++++++
 tests/test_refactor.py            | 802 ++++++++++++++++++++++++++++++++++++++
 tickets.md                        | 178 ++++++++-
 11 files changed, 2879 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_refactor.py::TestRunRefactor::test_rename_succeeds_and_commits` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestVerify::test_import_resolution_passes_clean_files` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestScanReferences::test_auto_alias_on_call_site_name_collision` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestRunRefactor::test_verify_failure_rolls_back` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestApplyPlan::test_apply_then_rollback_restores_tree` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestApplyPlan::test_overlapping_ops_refuse_before_write` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestApplyPlan::test_apply_failed_on_write_error_reports_apply_failed` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestRunRefactor::test_apply_failure_recovers_clean_precommit_tree` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestScanReferences::test_semicolon_joined_from_import_refuses_rewrite` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestScanReferences::test_unresolved_attribute_style_reference_surfaces` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestVerify::test_check_delta_uses_current_interpreter` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestVerify::test_import_resolution_catches_dangling_reference` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestVerify::test_import_resolution_local_import_resolves` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
