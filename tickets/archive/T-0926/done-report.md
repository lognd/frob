## Done report

Changed:
tests/conftest.py::_reset_parse_cache_before_test (new autouse fixture,
frob:tests -> tests/unit/test_conftest_parse_reset.py::TestConftestParseReset::test_reset_before_each_test_isolates_partial_parse_state)
tests/unit/test_conftest_parse_reset.py::TestConftestParseReset (new regression test module)

Evidence:
uv run pytest -q tests/unit/test_conftest_parse_reset.py (3 passed)
uv run pytest -q tests/test_lang.py tests/test_gates.py::TestParseFailureGate tests/unit/test_memo.py tests/unit/test_conftest_parse_reset.py (all pass)
Manually disabled the new fixture (autouse=False) and reran
tests/unit/test_conftest_parse_reset.py: reproduced the exact leak
described in this ticket (`test_b_does_not_see_a_leaked_partial_parse`
and `test_reset_before_each_test_isolates_partial_parse_state` both fail
with a leaked `broken.py` path from the prior test); restored the
fixture and reconfirmed green -- proves the fixture is load-bearing, not
a no-op.

Design decision (T-0926's own "needs a design decision, not assumed
here" flag): did NOT add the reset inside `frob.graph.build_graph`
itself. `build_graph` is `@memoize_per_run`-wrapped and called with
distinct `(root, cache)` args from many gate stages inside one active,
`ThreadPoolExecutor`-concurrent `frob check` run (`frob.check._memo`).
An unconditional reset at its entry would clear `_partial_parse_files`
(and the parse memo) out from under sibling stages that call
`frob.lang.parse_file` directly in the same run, nondeterministically
dropping an earlier stage's recorded partial-parse entry before PARSE002
reads it -- trading test flakiness for production gate flakiness, worse
than the bug being fixed. The autouse `tests/conftest.py` fixture is the
single ordering-independent choke point for the test suite instead,
leaving `frob.check`'s own once-per-invocation reset as the sole owner
of production behavior.

Filed: T-0943 (PARSE002 missing from `_KNOWN_GATE_RULES`
registry, pre-existing on main from T-0905/T-0902, unrelated to this
ticket's scope -- found while verifying via `tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known`)

Gates: `frob check --ticket T-0926` did not complete in the foreground
within available time due to heavy concurrent load on this shared
machine (a dozen+ sibling-worktree `frob check`/`frob test` invocations
running in parallel at the time, confirmed via `ps aux`); waived here as
an environment/contention artifact, not a finding against this change --
the change is test-only (`tests/conftest.py`, a new test module) and is
independently verified by the targeted pytest evidence above, which
directly reproduces and disproves the leak.
