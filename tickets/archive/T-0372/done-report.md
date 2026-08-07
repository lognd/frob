## Done report

Changed:
- src/frob/arch/__init__.py :: _analyze_one_file -- `_check_large_file` is now
  only called for files that have a tree-sitter grammar
  (`_has_tree_sitter_grammar`), i.e. real source; the call was moved to after
  the grammar check instead of running unconditionally on every file in the
  tree walk.
- src/frob/arch/__init__.py :: _check_large_file -- docstring updated to
  document the T-0372 caller-side gating; frob:ticket/frob:tests directives
  extended.
- tests/unit/test_arch.py :: TestLargeFile -- added
  test_large_json_data_not_flagged, test_large_md_ledger_not_flagged,
  test_large_py_src_still_flagged (1000-line fixtures per the ticket's
  acceptance criteria).

Chosen approach: the "only run the check when the file has a tree-sitter
grammar" predicate (not an explicit extension denylist) per the ticket's
suggested cleanest option -- this exempts .json/.md/.lock/.toml/.yaml and
any other extension with no registered grammar automatically, without a
second list to keep in sync with `frob.lang.tree_sitter_extensions()`.

Evidence (fresh `pytest --collect-only` resolved, `uv run frob test --base
main` selected and ran all 6 exactly, exit=0):
- tests/unit/test_arch.py::TestLargeFile::test_large_json_data_not_flagged
- tests/unit/test_arch.py::TestLargeFile::test_large_md_ledger_not_flagged
- tests/unit/test_arch.py::TestLargeFile::test_large_py_src_still_flagged
- tests/unit/test_arch.py::TestLargeFile::test_large_src_file_still_flagged
- tests/unit/test_arch.py::TestLargeFile::test_large_test_file_not_flagged
- tests/unit/test_arch.py::test_arch_end_to_end_analyze_then_render (pre-existing, unaffected, still passes)

Measured before/after (`uv run frob check --only arch`, large-file findings
only):
- Before (main tip 4895a05, in a scratch clone with `make core` built
  fresh): 60 large-file findings total, 26 of them non-source data/generated
  files (.frob-release.json, tickets-archive.md, tickets.md, CHANGELOG.md,
  uv.lock, docs/**/*.md, docs/design/registry/*.yaml, design/frob.strata).
- After (this worktree, post-fix): 34 large-file findings total, 0
  non-source -- every remaining hit is a real .py or .rs module (verified:
  `grep "large-file" ... | grep -Ev '\.(py|rs)\b'` returns nothing).

Filed: none (no out-of-scope work found).
Gates: `uv run frob check --ticket T-0372` clean -- exit 0, 0 errors, 1
warning (frob-arch itself, unrelated pre-existing warning tally), 41 waived
(all pre-existing, none touching this ticket's scope). Ruff/ty/frob-cycle/
frob-dup/frob-arch/exports all pass in the tool summary.
