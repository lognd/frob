## Done report

Root cause: the isolated-call-slower-than-in-context discrepancy Finding 5
flagged was NOT a GateConfig(root='.')/ticket-resolution divergence (the
leading hypothesis) -- _load_inputs resolves identically both ways
(4.5-5.5s). The slowdown was entirely inside test_gate itself: three
independent O(symbols x collected-node-ids) hot loops, invisible to every
prior pass because the profiler cannot see inside the thread-pool worker
`test` normally runs in (Finding 0).

1. `_inferred_unit_cases`/`_test015_record_violation`/
   `_test014_group_by_leaf`'s naming-convention fallback each called
   `_snake()` (two re.sub passes) on every one of ~6.4k collected node ids
   FROM SCRATCH, once per public symbol checked (~14.3k symbols) --
   O(14.3k x 6.4k) re-`_snake()` cost. Fixed with `_leaf_snake_index`
   (functools.lru_cache keyed on the CollectedTests value, a frozen/
   hashable pydantic model): every node id's snake-cased leaf computed
   once, reused by all three call sites.
2. `_node_id_collected`/`_case_count` each independently re-scanned the
   full collected-node-id set with a linear startswith() loop (~50M calls
   in the isolated profile) to answer "does a base[case-id] expansion of
   this base exist", once per edge/symbol. Fixed with `_case_ids_by_base`
   (lru_cache keyed on the node_ids frozenset): every collected id grouped
   by its pre-bracket base once, turning both call sites into O(1) dict
   lookups.
3. `_has_assertion_evidence` (T-0549) read_text()+ast.parse()'d its target
   test file from scratch on every call, even when several functions in
   the same file were each checked. Fixed with `_parsed_test_module`
   (lru_cache keyed on (file_path, mtime_ns, size) so a file edited
   mid-process transparently reparses instead of serving stale content):
   one parse per distinct file per run.

All three fixes are pure memoization over stable, hashable keys for the
run's duration -- test_gate's return value (violation set) is unchanged;
verified identical (15 violations) before and after every fix, and the
full tests/test_gates.py suite (463 collected) passes unchanged.

Before/after (isolated `test_gate(...)` call, `_load_inputs(GateConfig(
root='.'))` bypassing the thread pool per Finding 5's own method, natives
built, warm cache):

  before (Finding 5, this audit): did not complete within a 100s budget
  before, re-measured this pass:  105.7s (low host contention) / 166.5s
                                   (measured under concurrent-agent host
                                   contention -- load average 11.5/12
                                   cores from OTHER worktree agents on
                                   this shared box; time.process_time()
                                   was added to the harness to keep later
                                   numbers contention-insensitive)
  after fix 1 only (_leaf_snake_index):                        90.97s
  after fixes 1+2 (_case_ids_by_base added):                   17.82s
  after fixes 1+2+3 (_parsed_test_module added):                6.52s

Re-measured in real context: `uv run frob check --only gates-fast` now
reports test=2.22-3.15s (previously 12.36-13.68s per the audit's original
ranked table, row 2 / 15% of total). `frob check --ticket T-0949` (full
gate set) is clean: 0 errors across every gate, including gate:TEST (0
errors, 13 warnings, 2 waived, unchanged from before this ticket).

Appended a full write-up (root cause, all three fixes, before/after
numbers) to docs/audits/check-performance.md's own remediation log, per
this ticket's dispatch instructions -- scope was widened by one file
(docs/audits/check-performance.md) via `frob ticket scope --add` with a
recorded reason, since the ticket's original scope (src/frob/gates/**
only) did not include the audit doc T-0929 had scope for. No other file
outside declared scope was touched.

Filed: none. No out-of-scope bugs found; remaining rows in the audit's
ranked table (archgate, static, sys/secrets/pii_structural, dead_symbols,
etc.) are already covered by their own tickets (T-0930/T-0946/etc.) and
were not touched here.

Gates: `frob check --ticket T-0949` clean (0 errors, all gates pass,
including gate:TEST/gate:COV/gate:PRE after a fresh `frob ticket sweep
T-0949` following the scope change). `ruff check`/`ruff format --check`
clean on every file this ticket touched (the 2 ruff-format findings in the
full run are pre-existing, in unrelated files never touched by this
ticket: src/frob/arch/_lock_ordering.py, tests/unit/test_arch.py).

### Changed
```
 docs/audits/check-performance.md |  80 +++++++++++++++++++++++++
 src/frob/gates/__init__.py       | 125 +++++++++++++++++++++++++++++++++------
 2 files changed, 186 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTest014AmbiguousConventionMatch::test_fires_on_cross_file_same_test_collision` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTest014AmbiguousConventionMatch::test_silent_when_symbol_has_explicit_edge` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTest014AmbiguousConventionMatch::test_silent_when_no_leaf_name_collision` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTest015VacuousCredit::test_fires_on_no_op_test_body` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTest015VacuousCredit::test_silent_when_any_matching_test_asserts` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTest015VacuousCredit::test_silent_when_no_test_matches_at_all` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_test003_satisfied_by_parametrized_test_node_id` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_test003_satisfied_by_parametrized_case_with_dot_in_case_id` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_test002_parametrized_test_counts_each_case` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_test002_noop_parametrize_does_not_inflate_case_count` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_case_count_root_aware_caps_noop_parametrize` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 0 error(s), 4156 warning(s), 219 waived
- error-findings: none (measured, zero errors)
