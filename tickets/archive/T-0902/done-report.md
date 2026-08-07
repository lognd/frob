## Done report

Changed:
- src/frob/gates/_parse_failures.py::parse_failure_gate (frob:ticket/
  frob:tests directives only -- the PARSE002 implementation itself landed
  in T-0905, this ticket's paired fix)
- tests/test_gates.py::TestParseFailureGate.test_no_parse_failures_is_clean
  (added a `reset_parse_cache()` call to make it immune to the T-0905-
  filed cross-test leak, see below)
- tests/test_gates.py::TestParseFailureGate.test_partial_parse_is_an_error_violation
  (new)
- tests/test_gates.py::TestParseFailureGate.test_no_partial_parses_is_clean
  (new)

Added the PARSE002 regression tests this ticket exists for:
`test_partial_parse_is_an_error_violation` writes a fixture with a syntax
error partway through a file (`def good_one(): ...` then `def broken(:
...`), builds a real snapshot via `build_graph`, asserts the symbol BEFORE
the error (`good_one`) IS present in `snapshot.symbols` (proving the
salvaged-parse tradeoff is real, not just theoretical), then asserts
`parse_failure_gate` fires exactly one PARSE002 ERROR violation naming
`broken.py`. `test_no_partial_parses_is_clean` is the paired negative
case. Both explicitly call `frob.lang.reset_parse_cache()` before (and,
for the positive case, after) exercising the gate, to keep
`frob.lang._partial_parse_files`'s process-lifetime global state from
leaking into whatever test runs next in the same pytest-xdist worker.

Also hardened the pre-existing, otherwise-untouched
`test_no_parse_failures_is_clean` (T-0558) the same way: while verifying
T-0905, this test was observed to fail intermittently under xdist when
scheduled after another test that leaves a stale partial-parse entry in
the shared global (e.g. `tests/test_lang.py`'s partial-tree WARNING
test) -- calling `reset_parse_cache()` at its own start closes that hole
for this specific test without needing the broader cross-file fix
(tracked separately, see below).

Evidence: full chunked gate loop for this ticket --
`uv run frob check --ticket T-0902 --only lint` (0 errors), `--only
static` (0 errors), `--only gates-fast` (0 errors after `frob ticket
sweep T-0902` cleared a PRE001 stale-sweep finding; confirmed the real
repo's own `tests/fixtures/lang/broken.py` intentionally-malformed
fixture does NOT trigger a spurious PARSE002 in a real `frob check` run
-- it is parsed by other lang-conformance tooling outside the graph-
build/`parse_failures` gate's own snapshot, so no waiver was needed),
`--only gates-native` (0 errors), `--only gates-security` (0 errors).
`uv run pytest tests/test_gates.py::TestParseFailureGate -q` -- 4 passed.

Filed (already filed while working T-0905, not duplicated here):
T-0926 covers the broader cross-test-file leak class this
ticket's own `reset_parse_cache()` calls work around locally but do not
fully close (a `tests/conftest.py` autouse fixture is the recommended
fix, per that ticket's body).

Gates: `frob check --ticket T-0902` clean across all five stage groups
(lint/static/gates-fast/gates-native/gates-security), 0 errors in each;
no waivers needed.
