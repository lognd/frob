## Done report

`src/frob/ast` was already deleted from the working tree by an earlier
commit (5d70dad); `git log -- src/frob/ast` shows no path exists on HEAD
and no code under `src`/`tests` imports `frob.ast`. The only remaining
`src/frob/ast/**`-scoped work was the leftover duplication this ticket's
body actually describes: `frob.arch` and `frob.dup._legacy` each kept a
private `_child`/`_node_text` copy of the same `child_by_field_name`/decode
one-liners `frob.lang._common` already carries for its own walkers.

Changed:
- src/frob/lang/_common.py::child_by_field (new -- `node.child_by_field_name`
  wrapper, mirrors the existing `child_text`)
- src/frob/lang/__init__.py::child_by_field (new public wrapper)
- src/frob/lang/__init__.py::node_text (new public wrapper, alias of
  `_common.child_text` for raw-node callers outside the extraction pipeline)
- src/frob/lang/__init__.py::__all__ (added child_by_field, node_text)
- src/frob/arch/_nodes.py -- deleted (both functions now delegate to
  frob.lang)
- src/frob/arch/_python.py, src/frob/arch/_cpp.py -- import
  `child_by_field`/`node_text` from `frob.lang` instead of
  `frob.arch._nodes`
- src/frob/dup/_legacy_common.py -- `_child`/`_node_text` removed (kept
  `_sha16`, the one dup-specific helper); docstring updated
- src/frob/dup/_legacy.py, src/frob/dup/_legacy_py.py,
  src/frob/dup/_legacy_cpp.py -- import `child_by_field`/`node_text` from
  `frob.lang` instead of `frob.dup._legacy_common`
- tests/unit/test_lang_primitives.py::test_child_by_field_and_node_text_public_wrappers
  (new -- exercises both public wrappers against a real parsed tree)
- tickets.md -- scope extended to cover
  `tests/unit/test_lang_primitives.py` and `tickets.md` itself (both
  needed touching to land tests/evidence for this ticket); pre-work sweep
  re-run via `frob ticket sweep T-0043` after the extension

`src/frob/ast/**` and `src/frob/lang/**` scope globs otherwise
untouched beyond the above.

Evidence: tests/unit/test_lang_primitives.py::test_child_by_field_and_node_text_public_wrappers,
tests/test_lang.py::test_lang_pipeline_integration,
tests/unit/test_arch.py::test_arch_end_to_end_analyze_then_render,
tests/unit/test_dup.py::test_dup_end_to_end_scan_then_render (recorded via
`frob ticket evidence`)

Filed: none (no out-of-scope work found; the frob.ast deletion itself was
already done by a prior commit, nothing left to file)

Gates: `frob check --ticket T-0043` -- gates pass, 126 violation(s), 8
waived (same violation count as the pre-change baseline on `main`, diff
confined to line-number shifts and one abstraction-opportunity group that
shrank from 3 to 2 members because the `_node_text` triplication this
ticket removes was itself one of the flagged duplicates). `ruff check`,
`ruff format`, `ty check` all clean. `make test` -- full suite passes.
`frob test --base main` -- touched-set selection (5 tests) passes.
