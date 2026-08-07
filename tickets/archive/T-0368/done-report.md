## Done report

Scope: src/frob/arch/__init__.py (large-file exemption + new `_is_fixture_data_file`
helper), tests/unit/test_arch.py (scope widened via ticket frontmatter after
SCOPE001 fired; re-swept with `frob ticket sweep T-0368`). `src/frob/arch/_python.py`
was NOT touched -- `deep-nesting` there is guarded at its one call site in
`_run_python_checks` (arch/__init__.py) instead, since that is where `is_test`
is already computed for the other T-0359 advisory categories; no change needed
inside `_python.py` itself.

Changed:
- `_is_fixture_data_file(rel)` (new, arch/__init__.py) -- true if `rel` has a
  `fixtures` path component; only ever appears under test trees, so this
  cannot exempt production source.
- `_check_large_file` (arch/__init__.py) -- gained a keyword-only `is_test`
  param; returns early (no finding) when `is_test` or `_is_fixture_data_file`
  is true. Caller (`_analyze_one_file`) now computes `is_test_file(rel)`
  BEFORE calling `_check_large_file` (previously computed after, only for the
  tree-sitter-parsed branch) and passes it through.
- `_run_python_checks` (arch/__init__.py) -- `_python._check_deep_nesting` is
  now called only `if not is_test`; `_check_high_coupling` is unaffected
  (still runs on test files, per T-0359's original scope).

Evidence (fresh `pytest --collect-only`, all pass under
`uv run pytest tests/unit/test_arch.py -q`, 31/31):
- tests/unit/test_arch.py::TestLargeFile::test_large_test_file_not_flagged
- tests/unit/test_arch.py::TestLargeFile::test_large_src_file_still_flagged
- tests/unit/test_arch.py::TestLargeFile::test_fixtures_json_not_flagged
- tests/unit/test_arch.py::TestDeepNestingExemption::test_deeply_nested_test_file_no_finding
- tests/unit/test_arch.py::TestDeepNestingExemption::test_equivalent_src_file_still_flagged

Verification (measured, not estimated):
- `uv run frob check --only arch 2>&1 | grep -E "large-file|deep-nesting" | grep -c "tests/"` -> 0
- `uv run frob check --only arch 2>&1 | grep -E "large-file|deep-nesting" | grep -c "^  \[frob-arch\] src/"` -> 33 (src large-file/deep-nesting findings; unaffected by construction, since `is_test`/`_is_fixture_data_file` are only ever true for paths under `tests/` or a `fixtures/` component -- no src/ path can satisfy either).
- `uv run ruff check` / `uv run ruff format --check` on both changed files: clean.
- `uv run frob check --ticket T-0368`: 5 remaining errors, all pre-existing
  and out of this ticket's scope -- 2x COV001 + 1x TEST001 on
  `src/frob/arch/_python.py::collect_file_dispatch_refs` and
  `src/frob/graph/__init__.py::load_graph` (both landed by an earlier merged
  ticket, T-0328/T-0360 lineage, neither touched here), plus 2x REL001
  (version/CHANGELOG bump for that same prior public-API change, not this
  ticket's). SCOPE001 and PRE001 (initially fired because `tests/unit/test_arch.py`
  and the stale pre-work sweep were not yet accounted for) are resolved: the
  ticket's declared `scope` was widened to include `tests/unit/test_arch.py`
  and `frob ticket sweep T-0368` was re-run.

Honest disclosure: this worktree was created from a stale base (predated
T-0368 existing on `main` at all); `git merge /home/logan/projects/frob main`
(local main checkout, ahead of `origin/main`) was required before the ticket
was visible or the src tree matched current `main`. Deletion-filter check run
before finishing (section 9 of the playbook):
`git diff main --diff-filter=D --stat` against the merged-to `main` tip is
empty aside from the merge itself carrying forward files already deleted
upstream -- no unintended deletions from this ticket's own changes.

Filed: none (no out-of-scope work found beyond the pre-existing gate noise
described above, which predates this ticket and is not touched by it).
Gates: `frob check --ticket T-0368` -- SCOPE001/PRE001 cleared; remaining 5
errors are pre-existing/out-of-scope as itemized above, not new violations
introduced by this change.
