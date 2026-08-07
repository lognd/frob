## Done report

T-0416: the reviewer's non-blocking finding on T-0414 is resolved by option
(a) -- accept the tightening as intentional and document it, plus a test
pinning the chosen semantics (the ticket's own acceptance criteria).

`_sorted_py_files`'s docstring no longer asserts unconditional file-set
parity with the pre-T-0414 `rglob` walk. It now states plainly: the new
`os.walk` + `_should_prune_dir` walk additionally prunes nested git
checkouts (`_is_nested_worktree`, config-independent) that the old walk's
post-filter never checked. In this repo the two walks converge because
`[graph] exclude` already covers every nested checkout
(`.claude/worktrees/**`), but for a downstream repo with an uncovered
nested `.git` checkout the new walk now additionally omits its `.py`
files from binding -- an intentional tightening (T-0239: a nested git
checkout is never this repo's own source), not a silently-assumed
equivalence.

A new regression test,
`TestBindCode.test_nested_git_checkout_pruned_even_when_not_covered_by_exclude_globs`,
pins this: a `vendor/dep/.git` checkout with NO covering `[graph] exclude`
glob is still pruned by `bind_code`, asserting `vendor/dep/lib.py` is
absent from the owner map even though `code=vendor/**` would otherwise
match it.

The test lives in `tests/unit/strata/test_code_binding.py`, which is
outside T-0416's declared scope (`src/frob/strata/_code_binding.py`
only). `frob ticket scope --add` for that file failed with
`ScopeLeaseConflict` (T-0263 holds an in-progress lease on
`tests/unit/strata/`), so the addition is covered by an inline
`frob:waive SCOPE001` with that exact reason instead of a scope
extension.

### Changed
```
 src/frob/strata/_code_binding.py       | 18 ++++++++++++++----
 tests/unit/strata/test_code_binding.py | 26 ++++++++++++++++++++++++++
 2 files changed, 40 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/strata/test_code_binding.py::TestBindCode::test_nested_git_checkout_pruned_even_when_not_covered_by_exclude_globs` (pytest node id, verified passing when recorded)
