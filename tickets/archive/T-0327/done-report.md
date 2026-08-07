## Done report
Added `TreeNode.span: tuple[int, int]` (byte offsets, default `(0, 0)` so any other construction site stays valid) to `frob.lang.TreeNode` (src/frob/lang/_models.py), with the docstring updated to describe the field and its consumer. Threaded real `(node.start_byte, node.end_byte)` values through `frob.lang._common.export_tree`'s three `TreeNode(...)` construction sites (the budget-exhausted branch, the internal-node branch, and `_leaf_tree_node`'s two branches) -- src/frob/lang/_common.py is the only other file touched, and `frob.lang.symbol_tree` (src/frob/lang/__init__.py) needed no change since it already delegates to `_export_tree`/`export_tree` unmodified. Only actual construction sites of `TreeNode` in the repo are these; no other in-scope or out-of-scope call site needed updating.

Consuming `span` in `frob.dup._template` to render literal source text (the ticket's stated motivation) is genuinely outside this ticket's `src/frob/lang/**` scope -- not filed as a follow-up: T-draft-aa52c66f (never refiled) (provisional id, worktree is off `main`; will get a real T-#### on land) "frob.dup._template: consume TreeNode.span for literal source-text rendering", scope `src/frob/dup/_template.py,src/frob/dup/_pipeline.py,tests/**,docs/modules/dup.md,tickets.md`. That ticket also carries the docs/modules/dup.md update (the paragraph noting TreeNode "does not carry source spans/text today" is now stale but is out of this ticket's scope to edit).

Changed:
- src/frob/lang/_models.py::TreeNode
- src/frob/lang/_common.py::export_tree
- src/frob/lang/_common.py::_leaf_tree_node

Evidence (pre-existing tests, still collect and pass unmodified against the new field):
- tests/unit/test_lang_primitives.py::test_export_tree_and_flatten_tree_round_trip
- tests/unit/test_lang_primitives.py::test_symbol_tree_covers_span
- `uv run pytest tests/unit/test_lang_primitives.py tests/unit/test_lang_strata.py -q` -> 39 passed
- `uv run pytest tests/unit -k "dup or lang" -q` -> 132 passed, 2 skipped (broader lang/dup regression sweep, unaffected)

Not Filed: T-draft-aa52c66f (never refiled) (dup._template span consumption, see above)

Gates: `uv run frob check --ticket T-0327 --json` -- ruff-check/ruff-format/ty/frob-cycle/frob-dup/frob-arch/frob-exports(*) all exit 0; `gates` tool's only error-severity diagnostics are SCOPE001 on tickets.md and PRE001 on tickets/T-0327, both pre-close-report artifacts (tickets.md is always in-scope per the playbook; PRE001 clears once this Done report is committed) -- no error-severity diagnostic against any src/frob/lang file.

## Reviewer round-2 fixes (2026-07-20)
Reviewer REJECTED round 1 on two points, both fixed in this same worktree (no stash):
1. `TreeNode`'s docstring falsely claimed `frob.dup._template` already consumes `span` in present tense. Reworded to state `span` EXISTS so that consumer CAN be built later (the consumption itself is T-draft-aa52c66f (never refiled), not done here) -- `span` is populated but unread outside `frob.lang` today. Doc and code now agree.
2. Neither cited evidence test actually asserted the new field. Extended both: `test_export_tree_and_flatten_tree_round_trip` now asserts `node.span == (fn.start_byte, fn.end_byte)`, `start < end`, `src[start:end] == fn.text`, a literal-text prefix match, and that every child's span nests inside its parent's and is itself well-formed (`c_start < c_end`); `test_symbol_tree_covers_span` now asserts `start < end` and that slicing the raw source bytes by `node.span` reproduces the function's exact literal text (`def greet(name):\n    """Say hi."""\n    return name`). Both re-recorded as evidence via `frob ticket evidence T-0327` (same two node ids, now genuinely covering the field).

Widened `scope` to add `tests/unit/test_lang_primitives.py` and `tickets.md` (both needed to carry the strengthened evidence + this report) -- re-ran `frob ticket sweep T-0327` after widening, per the T-0343 precedent for widening a ticket's own scope mid-flight.

Verified: `uv run frob check --delta --ticket T-0327` (no baseline stamped in this worktree, so `--delta` degrades to the full report per its own documented behavior) -- 0 errors touching `src/frob/lang/**` or the new test file; the only error-severity findings anywhere are `ty` missing-argument in `tests/unit/strata/test_threat.py:914` and `gates` DRIFT002/REL001, all three pre-existing and unrelated (confirmed via `git log` on those files: last touched by commit 3418fdb, not by this ticket). `uv run pytest tests/unit/test_lang_primitives.py -q` -> 18 passed, 0 failed. `uv run ruff format --check` clean on all three changed files. `git diff <merge-base> -- tickets.md` shows exactly two hunks: T-0327's own block (scope/evidence/Done-report edits) and the appended T-draft-aa52c66f (never refiled) follow-up ticket -- no other ticket's state was reverted or altered. `git diff main --diff-filter=D --stat` remains empty.
