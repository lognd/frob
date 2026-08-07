---
id: T-0926
title: partial_parse_files() module-global state leaks across tests that call build_graph
  directly (PARSE002 flakiness)
state: done
kind: bug
origin: human
created: '2026-07-26'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/conftest.py
- src/frob/graph/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_conftest_parse_reset.py::TestConftestParseReset::test_a_leaves_a_partial_parse_behind
- tests/unit/test_conftest_parse_reset.py::TestConftestParseReset::test_b_does_not_see_a_leaked_partial_parse
- tests/unit/test_conftest_parse_reset.py::TestConftestParseReset::test_reset_before_each_test_isolates_partial_parse_state
designated_repro_test: null
threat: null
component: null
---
Found while working T-0905 (wiring `frob.lang.partial_parse_files()` into
the new PARSE002 gate).

`frob.lang._partial_parse_files` is a process-lifetime module-global set,
correctly reset exactly once per real `frob check` invocation
(`frob.check._run_check_with_skips` calls `reset_parse_cache()` before any
gate/snapshot work starts). That is sound for a real one-shot CLI run.

It is NOT sound for the test suite: `tests/test_gates.py::_snapshot` (and
several other test helpers) call `frob.graph.build_graph` directly,
bypassing `frob.check`'s reset entirely. Any earlier test in the same
pytest-xdist worker process that parses a file with a syntax error
(`_warn_if_partial_tree`) leaves its display path in
`_partial_parse_files` until some LATER test happens to call
`reset_parse_cache()` at its own start. Reproduced concretely: running
`tests/test_lang.py tests/test_gates.py::TestParseFailureGate` together
under xdist intermittently fails
`TestParseFailureGate.test_no_parse_failures_is_clean` (added T-0558,
unmodified) with a leaked PARSE002-shaped violation from an unrelated
tmp_path in `test_lang.py::TestParse::test_syntax_error_logs_partial_tree_warning`
-- purely because file collection/worker-assignment order happened to
place them adjacently with no intervening reset. Running the same two
files serially (`-n0`) happens to pass only because `test_lang.py`'s LAST
test (`test_cross_entry_point_reuse_is_one_parse_per_file`) incidentally
calls `reset_parse_cache()` at its own start, coincidentally scrubbing the
leak before `test_gates.py` runs -- an accident of file-internal test
order, not a real guarantee.

Net effect: before T-0905, nothing consumed `partial_parse_files()`, so
this leak was invisible. Now that `frob.gates._parse_failures.
parse_failure_gate` reads it directly (PARSE002), any test suite that
calls `build_graph` directly (not through `frob.check`) is exposed to
flaky PARSE002 assertions depending on pytest-xdist worker/test ordering
-- a real, if narrow, source of test flakiness going forward, and it will
grow as more tests call `parse_failure_gate`/`build_graph` directly (e.g.
T-0902's own regression tests, which had to add explicit
`reset_parse_cache()` calls around every case that reads
`partial_parse_files()`-backed data to route around it).

Fix direction: add an autouse `tests/conftest.py` fixture (or a narrower
one scoped to test modules that call `build_graph`/`parse_file` directly)
that calls `frob.lang.reset_parse_cache()` before each test, so the global
memo/partial-parse-set never carries state across test boundaries no
matter what order xdist picks. Alternative/complementary: have
`frob.graph.build_graph` itself call `reset_parse_cache()` internally at
the top of a fresh (non-incremental) build rather than relying on every
caller to remember, if that does not conflict with the incremental-cache
contract (T-0414) -- needs a design decision, not assumed here.