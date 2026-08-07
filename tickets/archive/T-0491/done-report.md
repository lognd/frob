## Done report

Extended the T-0423 run-scoped memoization pattern to `frob.dup.find_duplicates`
(src/frob/dup/_legacy.py), decorating it with `frob.check._memo.memoize_per_run`
at its definition site, matching the `build_graph`/`analyze_project` precedent.
This covers all four existing callers (frob.check._python._run_dup,
frob.gates._prework, frob.gates._arch, frob.app.dup_runner) automatically with
no call-site edits.

Added two tests to tests/unit/test_memo.py:
- test_find_duplicates_second_call_is_memo_hit: proves a second call with the
  same (root) inside one run_memo_scope returns the identical object (memo
  hit, 1 hit / 1 miss).
- test_find_duplicates_no_cross_run_leak: proves two independent
  run_memo_scope blocks each get their own fresh miss -- no cross-run
  staleness leak (0 hits / 1 miss in each scope, equal-but-not-identical
  results).

Wall-clock measurement (honest disclosure): ran `uv run frob check --ticket
T-0491` timed, with and without the decorator (temporarily reverted the
decorator/import-usage in a scratch copy, reran, restored). Both configurations
measured 21-26s wall time for the full ticket-scoped check on this repo, with
per-stage instrumentation showing clones=0.00s / prework=0.00s in both cases --
no macroscopic wall-clock difference was observable at this repo's current
size/call pattern; the noise floor (refs=6.3-6.7s, pii_structural=3.4-3.6s,
perf=2.9-3.0s dominate the total) swamps whatever redundant find_duplicates
rescans previously cost. The concrete, measured win is the memo-hit guarantee
itself (proven by the two new tests: a real scan is skipped and an identical
object is returned on the second call within one run), not a proven top-line
`frob check` wall-clock reduction at this repo's current scale -- disclosing
this plainly rather than claiming a speedup I did not observe.

REL001: the decorated function's docstring changed (public symbol content
change), so `frob release check` demanded a version bump. Bumped
pyproject.toml from 0.49.0 to 0.50.0 and ran `frob release stamp`.
Scope was extended (frob ticket scope --add) to cover tests/unit/test_memo.py,
pyproject.toml, .frob-release.json, and uv.lock (uv.lock's single-line diff
was already present in the tree before this ticket started; not otherwise
touched).

Pre-existing gate failures observed and NOT fixed (out of scope for T-0491):
- gate:DOC (DOC003, docs/commands/sys.md CWE-78 owasp-top-10 exhaustiveness
  claim) -- unrelated repo-wide baseline issue, already tracked separately
  (T-0508 per the ledger).
- gate:TICK (TICK003, 62 closed tickets sitting un-archived, threshold 60) --
  global housekeeping, unrelated to this ticket's scope.
Both were present identically before and after this ticket's changes.

### Changed
```
 .frob-release.json      |  2 +-
 src/frob/dup/_legacy.py | 16 +++++++++++++++-
 tests/unit/test_memo.py | 41 +++++++++++++++++++++++++++++++++++++++++
 3 files changed, 57 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_memo.py::test_find_duplicates_second_call_is_memo_hit` (pytest node id, verified passing when recorded)
- `tests/unit/test_memo.py::test_find_duplicates_no_cross_run_leak` (pytest node id, verified passing when recorded)
