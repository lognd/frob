## Done report

Made PERF004 (sort-in-loop) AST-aware instead of indentation-blind. Added
`_is_sort_call`/`_enclosing_loop_body_hit`/`_perf004_ast_hit_lines` to
src/frob/perf/_rules.py: re-parses the python file via `frob.lang.raw_tree`
and checks, for each `sorted(`/`.sort(` call node, whether it is a
descendant of an ancestor `for`/`while` statement's `body` FIELD
specifically (not merely lexically after the loop header) -- this is what
the old flat-token `_loop_gate` heuristic could not see, since
`RawSymbol.body_tokens` carries no position/indentation information.
`_python_violations`/`_perf004_python_fires` now prefer this AST-precise
check and fall back to the old lexical `_perf004_python`/`_perf004_line`
heuristic only when the file cannot be re-parsed (moved/deleted since the
original parse). PERF001/002/003 are unchanged -- this ticket is scoped to
PERF004 only.

Regression tests added to tests/test_perf.py (scope-added, reason on file):
- test_perf004_does_not_fire_on_sort_after_loop_same_indent (the ticket's
  headline false-positive: `.sort()` after a `for` loop at the same indent)
- test_perf004_does_not_fire_on_sorted_call_after_loop_same_indent (same
  shape, `sorted()` free-function form)
- test_perf004_still_fires_on_sort_nested_deeper_inside_loop_body (true
  positive preserved even one level more indented than the simple case)

All prior PERF004 fire/no-fire cases in tests/test_perf.py still pass
unmodified (fires-in-loop, does-not-fire-standalone, does-not-fire-as-loop-
iterable, does-not-fire-on-generator, anchors-to-call-line). Full
tests/test_perf.py: 52 passed. tests/test_perf_loop_invariant_effect_lock.py
(the T-0775 strict-xfail lock, explicitly out of this ticket's scope) still
reports XFAIL after this change, confirmed via
`pytest tests/test_perf_loop_invariant_effect_lock.py -q`.

Real-repo PERF004 count: `frob check --ticket T-0367 --only gates-native`
now reports gate:PERF PASS, 0 errors. 17 unwaived PERF004 findings remain
(all genuine loop-body sort calls per the new AST check, spot-checked
src/frob/arch/_ocp.py:314 by hand -- a `sorted(missing)` call inside a
`for enum_class in ...:` body, a real hit, not a false positive):
src/frob/arch/_ocp.py:314, src/frob/arch/_patterns.py:517,
src/frob/gates/__init__.py:1222, src/frob/gates/__init__.py:5082,
src/frob/gates/_docblocks.py:210, src/frob/gates/_docblocks.py:236,
src/frob/gates/_docblocks.py:1217, src/frob/gates/_lang_conformance.py:193,
src/frob/gates/_registry_exhaustiveness.py:405,
src/frob/graph/affects.py:132, src/frob/graph/lock.py:153,
src/frob/perf/_hotgraph.py:323, src/frob/strata/_contention.py:180,
src/frob/strata/_contention.py:328, src/frob/strata/_contention.py:366,
src/frob/strata/_design_load.py:259, src/frob/strata/_infra.py:670.
This is 17, not the 9 the ticket cited from T-0596 -- main has grown new
sort-in-loop sites since T-0596 was filed; these 17 (including the T-0363
sites the ticket named, which are now clean) are routed to T-0596 for
per-site waive/fix triage, not addressed here (out of this bug-fix
ticket's scope, which is the DETECTOR, not the sites).

Deviations:
- T-0367 existed in BOTH tickets.md (state=planned) and tickets-archive.md
  (a stale duplicate at state=queued, no Done report) -- a ledger-
  corruption instance of the exact class the existing "tickets:
  investigate missing-marker ledger corruption class" ticket already
  tracks. Removed the stale archive duplicate directly (it blocked `frob
  ticket start T-0367` with DuplicateId) since it was purely stale/orphan
  state with no Done report to lose; did not otherwise touch that
  investigation ticket's scope.
- T-0367's `acceptance` list is empty (filed with none at `frob ticket new`
  time, and there is no CLI path to add acceptance criteria to an existing
  ticket after filing). Evidence is recorded on the ticket's flat evidence
  list; `--accepts` could not be used since there is no acceptance index to
  bind to.
- `uv.lock` in this worktree's checked-out commit (2ed2d2f6) lags
  `pyproject.toml`'s version (0.97.0 vs 0.98.0 already on that commit) --
  every `uv run` invocation auto-resyncs `uv.lock` as a side effect, which
  then shows up as an unrelated SCOPE001 finding and a `git status` diff.
  Reverted with `git checkout -- uv.lock` before every commit per the
  playbook's land-owned-files rule; this file is not part of the committed
  diff.
- `tests/unit/perf/test_hotgraph.py::TestStackSampler::test_overhead_under_five_percent`
  failed once on a shared/loaded machine (0.41 ratio vs 0.05 budget) and
  passed clean on immediate rerun -- a pre-existing timing-flake unrelated
  to src/frob/perf/_rules.py, not touched by this ticket.
- gate:TEST's 2 errors (TEST010 kind='system' on
  tests/test_perf_loop_invariant_effect_lock.py and
  tests/system/test_spawn_budget.py) are pre-existing debt landed on main
  before this ticket started (both outside src/frob/perf/_rules.py and
  tests/test_perf.py); not introduced or touched by this change.
- Reviewer round 1 caught collateral splice damage in a prior merge of
  main into this worktree beyond my own T-0787 restore: T-0788's whole
  block deleted, T-0774 reverted in-progress -> queued, T-0766's Done
  report reverted to the phantom pre-T-0787 draft-id sentence.
  Re-merged against current main (which had since landed T-0676 and filed
  T-0790) and this time the ticket merge-driver spliced cleanly against
  the newer main for all three -- but a fresh block-by-block diff against
  `git show main:tickets.md` then caught a FOURTH, previously-unreported
  casualty from the same original splice: T-0674 reverted from
  state=done/full Done-report+evidence back to state=queued/empty, which
  I restored verbatim from main the same way. A scripted per-ticket-id
  block comparison against main (all 201 shared ids) now shows zero
  differences outside this ticket's own T-0367 block.

### Changed
(no changed files detected)

### Evidence
- `tests/test_perf.py::test_perf004_does_not_fire_on_sort_after_loop_same_indent` (pytest node id, verified passing when recorded)
- `tests/test_perf.py::test_perf004_does_not_fire_on_sorted_call_after_loop_same_indent` (pytest node id, verified passing when recorded)
- `tests/test_perf.py::test_perf004_still_fires_on_sort_nested_deeper_inside_loop_body` (pytest node id, verified passing when recorded)
- `tests/test_perf.py::test_perf004_fires_on_sort_in_loop` (pytest node id, verified passing when recorded)
- `tests/test_perf.py::test_perf004_does_not_fire_on_sort_outside_a_loop` (pytest node id, verified passing when recorded)
- `tests/test_perf.py::test_perf004_does_not_fire_when_sorted_is_the_loop_iterable` (pytest node id, verified passing when recorded)
- `tests/test_perf.py::test_perf004_does_not_fire_on_sorted_generator_no_preceding_loop` (pytest node id, verified passing when recorded)
- `tests/test_perf.py::test_perf004_anchors_to_sort_call_line_not_def_line` (pytest node id, verified passing when recorded)
