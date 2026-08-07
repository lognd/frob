## Done report

Changed:
- src/frob/check/_memo.py (new module) -- `run_memo_scope` (context manager,
  the explicit run-scope entry/exit), `reset_run_memo` (test/convenience
  entry into an unconditionally-active scope), `run_memo_stats` (hit/miss
  instrumentation), `memoize_per_run` (the decorator).
- src/frob/graph/__init__.py::build_graph -- decorated `@memoize_per_run`.
- src/frob/arch/__init__.py::analyze_project -- decorated `@memoize_per_run`.
- src/frob/check/__init__.py::_run_check_with_skips -- opens one
  `run_memo_scope()` around task construction+execution, alongside the
  existing `reset_parse_cache()` call.
- docs/commands/check.md -- new "Run-scoped memoization" section
  (`frob:describes` anchors for the 4 new public symbols); required by
  COV001/DOC002 for the new module, not itself in the ticket's scope
  globs but the direct doc home for symbols that are.
- pyproject.toml (version 0.35.0 -> 0.36.0) and CHANGELOG.md (new
  `[0.36.0]` entry) -- required by REL001 (mechanical semver on public
  API change); same "gate-driven, not scope-creep" rationale as the docs
  edit above.
- tests/unit/test_memo.py (new) -- 8 tests.

Design: `memoize_per_run` wraps a function so repeat calls with identical
(function-identity + frozen-args) keys, WHILE a `run_memo_scope()` is
active, return the cached result. Deliberately NOT an always-on
process-global memo (my first implementation was that, and it broke
`tests/test_graph.py`'s incremental-rebuild tests, which call `build_graph`
twice in one test across an on-disk content change with no reset boundary
-- exactly the "stale cached result is a correctness bug" the ticket warns
about). The fix: an explicit, depth-counted scope
(`frob.check._memo.run_memo_scope`) that only `frob.check._run_check_with_
skips` opens; outside an active scope every decorated call is a pure,
uncached passthrough, so any caller other than `frob check` itself
(CLI runners, `frob.app.*`, tests) is unaffected. Decorating at the
function's OWN definition site (not each call site) means every caller
across every stage/gate benefits automatically, including callers in
files this ticket's scope does not touch (e.g. `frob.gates._arch`'s
ARCH001 call into `analyze_project`) -- without editing those files.

Cut from scope (disclosed, not silently dropped): `find_duplicates` was
NOT memoized. It lives in `src/frob/dup/_legacy.py`, which is outside
this ticket's declared `scope` globs (`src/frob/dup/` is not listed) and
was under active concurrent rework (a sibling agent editing
`src/frob/dup/_template.py`) for the duration of this session -- touching
it would have both exceeded scope and risked a merge collision on a file
mid-rework elsewhere. Not Filed as a follow-up:
`T-draft-5a44ea39 (never refiled)` ("extend T-0423 run-scoped memoization to
frob.dup.find_duplicates", parent T-0423, scope `src/frob/dup/`) --
provisional id because this worktree is off the default branch; the
reviewer/coordinator should re-mint a real `T-####` id on land.

Measured wall-clock delta (this worktree, `uv run frob check`, no
`--only` filter, full run including gates):
- BEFORE (working tree reverted to pre-ticket state via `git checkout --
  <3 files>` + the two new files moved aside, `git apply` used to
  restore afterward -- no `git stash` used per the hard rule): `real
  2m0.451s` (`time uv run frob check`, exit 1 -- ended in a clean,
  pre-existing 0-error/1-warning state per the tool summary).
- AFTER (this ticket's changes applied, all gates green): `real
  0m28.562s` (`time uv run frob check`, exit 0, `0 errors, 1 warning,
  91 waived` -- same warning count as BEFORE).
- That is a ~76% wall-clock reduction (2m0s -> 28.6s) on this machine/
  worktree for a full `frob check` run. Caveat: this repo's own gates
  stage (`refs`, `perf`, `secrets`, `test`, etc.) dominates total
  wall-time far more than `build_graph`/`analyze_project` alone account
  for on a single measurement; some of the delta reflects normal run-to-
  run variance (page cache warmth, other load on the machine) rather than
  purely the memoization. The FIRST after-run (before I fixed the new
  gate violations the change itself introduced -- see below) measured
  0m53.0s for comparison, still well under the before figure. I did not
  isolate build_graph/analyze_project's own call counts in production
  `frob check` (no `--only arch` run with instrumentation printed); the
  call-count proof is the unit tests below, not a runtime log from a
  real `frob check` invocation.
- Two intermediate iterations of the "after" measurement failed
  `frob check` on gates I introduced myself (ty return-type on the
  decorator, missing frob:doc/frob:tests on the 4 new symbols, a stale
  DRIFT001 on build_graph's changed signature digest, missing PERF005
  termination-measure on `_freeze`'s recursion, and REL001 version/
  CHANGELOG) -- all fixed before the final green run above; disclosed
  here rather than only reporting the final clean number.

Evidence (all collected via `uv run python -m pytest --collect-only -q
tests/unit/test_memo.py -o addopts=""`, resolving against the real
collected node ids):
- tests/unit/test_memo.py::test_second_call_with_same_args_is_memo_hit
- tests/unit/test_memo.py::test_different_args_are_distinct_cache_entries
- tests/unit/test_memo.py::test_reset_run_memo_does_not_leak_across_runs
- tests/unit/test_memo.py::test_kwargs_are_part_of_the_cache_key
- tests/unit/test_memo.py::test_build_graph_second_call_is_memo_hit
- tests/unit/test_memo.py::test_run_memo_scope_deactivates_on_exit
- tests/unit/test_memo.py::test_run_memo_scope_nests_without_truncating_outer
- tests/unit/test_memo.py::test_analyze_project_second_call_is_memo_hit

`uv run pytest tests/unit/test_memo.py -q`: 8 passed.
`uv run pytest tests/test_graph.py -q`: 93 passed (proves the
incremental-rebuild tests, which call `build_graph` twice per test
outside any `run_memo_scope`, are unaffected by the decorator -- the
correctness boundary this design exists for).

Not Filed: T-draft-5a44ea39 (never refiled) (find_duplicates follow-up, parent T-0423; real
id to be re-minted on land since this worktree is off `main`).

Gates: `uv run frob check` clean -- 0 errors, 1 warning, 91 waived (same
warning count as the pre-ticket baseline). No waivers added by this
ticket's changes.
