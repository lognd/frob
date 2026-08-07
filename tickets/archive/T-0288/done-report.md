## Done report

Changed:
- `src/frob/graph/callgraph.py` (NEW): `CallGraph`, `build_call_graph`,
  `closure` -- the shared interprocedural call-graph substrate (private
  callees only recorded as edges, so `closure` stops at the public-API
  boundary for free; depth+node-cap+cycle-guard bounded BFS).
- `src/frob/dup/_pipeline.py`: `_body_tokens_for_symbol` now runs
  `_inline_private_calls` (in-place, recursive, bounded call-splicing via
  `_substitute_calls`/`_callee_name_map`/`_callee_tokens`/
  `_call_graph_for_path`/`_package_paths`) BEFORE the `min_tokens` floor
  check, so a thin wrapper around real private-helper logic is measured
  by that real logic. New `find_helper_clones` + `_is_private_helper`:
  dedicated population pass over private/module-local FUNCTION/METHOD
  symbols at `DupConfig.helper_min_tokens` (default 8) instead of
  `min_tokens` (default 40).
- `src/frob/dup/_models.py`: `DupConfig.inline_calls` (default True),
  `inline_max_depth` (3), `inline_max_nodes` (12), `helper_min_tokens` (8).
- `src/frob/dup/__init__.py`: export `find_helper_clones`.
- `docs/modules/dup.md`: new "Helper-inlining triage (T-0288)" section +
  `find_helper_clones` public-API-reference entry.
- `docs/modules/graph.md`: new "Call graph" section documenting
  `frob.graph.callgraph`'s API for T-0290 reuse.
- `tests/test_dup_inline.py` (NEW, 9 tests), `tests/fixtures/dup_inline/`
  (NEW fixture package: `mod_a.py` -- the helper-inlining litmus,
  `mod_b.py` -- the tiny-helper-population litmus).
- `CHANGELOG.md`: T-0288 entry under `[0.12.0] - unreleased`.
- `pyproject.toml`: version 0.11.0 -> 0.12.0 (additive public API,
  minor bump per T-0326/REL001); `.frob-release.json` restamped;
  `uv.lock` regenerated.

Litmus (both verified passing):
1. **Split-detected**: `process_orders`/`process_receipts`
   (`tests/fixtures/dup_inline/src/mod_a.py`) each call a differently
   named private helper (`_finalize_a`/`_finalize_b`) carrying the real
   shared logic; wrapper bodies alone are 5 tokens (below
   `min_tokens=12`) so `find_clones(..., inline_calls=False)` never even
   fingerprints them (`test_split_helpers_missed_without_inlining`
   asserts no match); `find_clones(..., inline_calls=True)` inlines the
   private-helper bodies in place, crosses the token floor, and reports
   the pair (`test_split_helpers_detected_with_inlining`).
2. **Over-split-caught**: `_clamp_a`/`_clamp_b`/`_clamp_c`
   (`tests/fixtures/dup_inline/src/mod_b.py`) are near-identical tiny
   private helpers (well under the whole-symbol `min_tokens=40` default);
   `find_helper_clones` (at `helper_min_tokens=8`) reports a clone pair
   among them (`test_tiny_helpers`); `test_helper_pass_excludes_public_symbols`
   confirms the public `normalize`/`public_entry`/`unrelated_thing`
   symbols never appear in that pass's output.
3. **Bounds, tested directly against `frob.graph.callgraph`**:
   `test_closure_is_cycle_guarded` (mutual `_x`<->`_y` recursion returns
   exactly one node, no infinite loop), `test_closure_respects_node_cap`
   (10 callees, `max_nodes=3` -> len==3), `test_closure_respects_depth_cap`
   (`_a->_b->_c->_d` chain, `max_depth=1` -> only `_b` reached),
   `test_public_callee_never_becomes_an_edge` (a call to public
   `normalize` from `public_entry` never appears in `graph.calls` at all
   -- confirms the public-API-stopping property is structural, not a
   runtime check).

Evidence (fresh `pytest --collect-only tests/test_dup_inline.py`, all 9
node ids collected and passing):
- `tests/test_dup_inline.py::TestHelperInliningLitmus::test_split_helpers_detected_with_inlining`
- `tests/test_dup_inline.py::TestHelperInliningLitmus::test_split_helpers_missed_without_inlining`
- `tests/test_dup_inline.py::TestHelperPop::test_tiny_helpers`
- `tests/test_dup_inline.py::TestHelperPop::test_helper_pass_excludes_public_symbols`
- `tests/test_dup_inline.py::TestCallGraphBounds::test_call_edge`
- `tests/test_dup_inline.py::TestCallGraphBounds::test_closure_is_cycle_guarded`
- `tests/test_dup_inline.py::TestCallGraphBounds::test_closure_respects_node_cap`
- `tests/test_dup_inline.py::TestCallGraphBounds::test_closure_respects_depth_cap`
- `tests/test_dup_inline.py::TestCallGraphBounds::test_public_callee_never_becomes_an_edge`
Also ran green (no regression): `tests/test_dup_smart.py`,
`tests/test_dup_region.py`, `tests/test_dup_rungs.py`,
`tests/unit/test_dup_core.py`, `tests/unit/test_dup_cache.py`,
`tests/unit/test_dup.py`, `tests/unit/test_dup_smt.py`,
`tests/unit/test_dup_template.py`, `tests/system/test_cli_dup.py` (full
`tests/ -k "dup or graph or callgraph"` run: 165 passed, 2 skipped).

Filed: none.

Gates: `frob check --ticket T-0288` clean of errors in scope (`frob
ticket sweep T-0288` re-run after a fresh `git merge main`). The only
remaining COV003 error in the full `frob check` output is on
`tickets/T-0214`, a pre-existing, already-documented (see this file's
earlier T-0214/T-0223 Done-report notes) unrelated-ticket baseline
finding, not touched by this change. `ruff check`/`ruff format
--check`/`ty check` clean on every touched file (both PATH `ruff` and
`uv run ruff`). `git diff main --diff-filter=D --stat` empty (deletion-
filter clean) after the T-0288 branch re-merged `main` (tip `c82028b`).
`frob release stamp` run; `.frob-release.json` diff is empty (no drift
from the earlier stamp).

Call-graph module API (for T-0290 reuse), `src/frob/graph/callgraph.py`:
```python
class CallGraph(BaseModel):          # frozen; caller-symref -> callee-symref, PRIVATE only
    calls: Mapping[str, tuple[str, ...]] = {}

def build_call_graph(root: Path, paths: Sequence[str]) -> CallGraph
    # paths: repo-root-relative POSIX files (typically one package/dir).
    # Records an edge only when the callee's short name starts with "_".
    # A call to a PUBLIC symbol is never an edge -- this alone makes
    # `closure` stop at the public-API boundary, no separate check needed.

def closure(graph: CallGraph, start: str, *,
            max_depth: int = 3, max_nodes: int = 12) -> tuple[str, ...]
    # Bounded BFS: depth-limited, node-count-capped, cycle-guarded
    # (visited set). Breadth-first order, `start` excluded.
```
Inlining bounds actually used by dup (`DupConfig`): `inline_calls=True`,
`inline_max_depth=3`, `inline_max_nodes=12`, `helper_min_tokens=8`.
dup's own splicing (`_substitute_calls` in `_pipeline.py`) does NOT call
`closure()` directly -- it needs in-place token substitution (replacing
the `name(...)` call span with the callee's body tokens, recursively) so
that inlined token ORDER matches between two differently-split callers;
a naive append-at-the-end splice (the first draft) failed the split-
detected litmus because token order diverged whenever the wrapper's own
prefix differed. It reimplements the same three bounds (depth, node
budget, cycle guard via a `visited` frozenset) directly over
`CallGraph.calls`, so the bound semantics are identical to `closure`'s,
just applied as a substitution walk instead of a reachable-set walk.
`closure()` itself remains a general-purpose, directly-tested utility
for a future consumer (T-0290) that wants the reachable set rather than
an in-place splice.

## Round 2: reviewer-rejected FALSE POSITIVE fix (shared-helper inflation)

Reviewer reproduced a real FP in the helper-inlining triage: two
UNRELATED functions (distinct own-logic) that both call the SAME shared
private helper were being reported as a clone pair once inlining spliced
the shared helper's body into both sides, letting the shared text (not
either caller's own logic) drive the similarity score above threshold.
Repro (`tests/fixtures/dup_inline/src/mod_c.py`, `_validate` called by
both `handle_shipping` and `handle_greeting`): `inline_calls=False` -> 0
groups (bodies too small to clear `min_tokens=40` un-inlined, so never
even compared -- correct); `inline_calls=True` -> 1 group at similarity
0.7083333333333333, both at the default threshold (0.85) and at 0.7 --
a false positive, since the two callers' only commonality is calling the
same helper (code reuse), not near-identical logic of their own.

Core distinction: sharing a helper is normal code reuse, not
duplication. Only DIFFERENTLY-NAMED, near-identical helpers
(`_finalize_a`/`_finalize_b`, the original litmus) are split-duplication.

Fix (approach (a) from the reviewer's brief -- do not let a helper both
sides call inflate similarity, rather than trying to discount/normalize
its contribution after the fact): `_pipeline.py` now computes, per
package directory and cached on `_FpState.caller_counts_by_dir`, a
`{callee_symref: caller_count}` map over `CallGraph.calls`
(`_caller_counts`). `_substitute_calls` only inlines a callee whose
caller count is `<= 1` -- a private helper reached by more than one
caller anywhere in the package is left as an opaque, un-substituted call
token on every side, so it contributes ordinary "same call" weight, not
duplicated-body weight. A helper with exactly one caller still gets
inlined and recursively expanded, which is exactly what the true
positive needs: two differently-named, each-singly-called helpers with
near-identical bodies still get spliced in and compared.

Chosen over option (b) (discount/normalize shared-subtree contribution
after inlining, require a residual floor) because (a) is simpler to
reason about and directly encodes the "shared = reuse, not dup" rule at
the point inlining decides what to expand, rather than trying to
retroactively separate "shared" from "own" tokens inside an already-
merged stream.

Verification (this round, `frob_core` present):
- `tests/test_dup_inline.py::TestSharedHelperNotDuplication::test_shared_helper_not_flagged_at_default_threshold`
  and `::test_shared_helper_not_flagged_at_threshold_0_7` (new adversarial
  regression, reviewer's exact repro shape): confirmed FAILING against
  the pre-fix `_pipeline.py` (reproduces the FP at 0.708 similarity, both
  default threshold 0.85 and 0.7), PASSING after the fix.
- `test_split_helpers_detected_with_inlining` (the original true
  positive, `_finalize_a`/`_finalize_b` singly-called differently-named
  twins) still green -- the fix does not regress detection.
- `uv run pytest tests/test_dup_inline.py tests/test_dup_smart.py
  tests/test_dup_rungs.py -q`: all green.
- `frob dup src --json` group count on frob's own tree: 14 groups before
  and after the fix (compared by temporarily reverting only
  `_pipeline.py` via `git stash`/`git checkout --`) -- no false-positive
  or false-negative delta introduced by the fix on this repo's own
  clones.
- `ruff check src/ tests/`, `ruff format --check` (touched files), `ty
  check src/`: all clean.
- `make coverage` (foreground): full suite green, coverage stamped
  (`source_sha=c3b0d6ff`).

Reconcile note (reviewer): `_substitute_calls` reimplements
`frob.graph.callgraph.closure`'s bounds (depth cap, node budget, cycle
guard) rather than calling `closure` directly -- documented in a comment
directly above `_substitute_calls` in `_pipeline.py`: `closure` returns a
flat, precomputed BFS symref order, while `_substitute_calls` needs
interleaved TOKEN splicing where which callee to expand next depends on
where its call-span lands inside the already-substituted token stream of
its caller, and each splice consumes the shared budget before the next
call site is even scanned -- not something `closure`'s return shape
supports without changing it. Left as a note (not a forced reuse) per
the reviewer's "if not cheap" fallback; `callgraph.py` itself is
untouched this round.

Not touched this round (per dispatch instructions): `callgraph.py` /
`closure` bounds themselves -- those passed review and are out of scope
for this FP fix.
