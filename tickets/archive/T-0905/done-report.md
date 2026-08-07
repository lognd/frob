## Done report

Changed:
- src/frob/gates/_parse_failures.py::parse_failure_gate
- src/frob/gates/_parse_failures.py::_partial_parse_violations (new)
- src/frob/lang/__init__.py::partial_parse_files (docstring only)
- src/frob/lang/__init__.py::_warn_if_partial_tree (docstring only)
- docs/modules/gates.md (rule-catalog: added PARSE001 + PARSE002 rows;
  PARSE001's row had been missing from the table entirely -- a
  pre-existing gap, fixed alongside PARSE002 since both anchor there)
- docs/modules/lang.md (Parse cache section: partial_parse_files()
  signature + explanatory paragraph, frob:describes anchor added)

Wired `frob.lang.partial_parse_files()` into `frob check` as PARSE002, an
ERROR-tier violation symmetric with PARSE001's hard-failure handling.
Reused the existing "parse_failures" gate job entry
(`frob.gates._parse_failures.parse_failure_gate`, already registered in
`frob.gates._ALL_GATES`/`_build_jobs`) rather than adding a new
gate-dispatch entry: `parse_failure_gate` now also calls a new private
`_partial_parse_violations()` helper that reads
`frob.lang.partial_parse_files()` directly (not threaded through
`GraphSnapshot`) and emits one PARSE002 ERROR `Violation` per entry. No
`gates/__init__.py` changes were needed.

Scope was extended +docs/modules/gates.md +docs/modules/lang.md (recorded
via `frob ticket scope --add ... --reason ...`, see scope_changes above)
once AFFECT001 required touching the affects()-closure docs for
`parse_failure_gate`/`partial_parse_files`.

Evidence: ran the full chunked gate loop for this ticket --
`uv run frob check --ticket T-0905 --only lint` (0 errors after a line-
length fix), `--only static` (0 errors; PARSE001/PARSE002 rows resolved
AFFECT001, `frob ticket sweep T-0905` cleared the resulting PRE001 stale-
sweep finding), `--only gates-fast` (0 errors), `--only gates-native`
(0 errors), `--only gates-security` (0 errors). Ran the pre-existing
PARSE001 regression tests plus the existing partial-tree WARNING test as
regression evidence: `uv run pytest tests/test_gates.py::TestParseFailureGate
tests/test_lang.py::TestErrors::test_syntax_error_logs_partial_tree_warning
-q` -- both pass. No new test file added here since `tests/test_gates.py`
is not in this ticket's declared scope; the paired T-0902 ("add PARSE002
gate wiring ... + regression test") owns adding the new PARSE002-specific
test cases there, next in this worktree's sequence.

While verifying, found a real (if narrow) test-isolation hazard, out of
this ticket's scope: `frob.lang._partial_parse_files` is a process-
lifetime module-global, correctly reset once per real `frob check` run,
but `tests/test_gates.py`'s `_snapshot()` helper (and similar helpers)
call `frob.graph.build_graph` directly, bypassing that reset -- under
pytest-xdist, an earlier test in the same worker that parses a syntax-
error fixture can leak a stale PARSE002-shaped entry into a later,
unrelated test. Reproduced concretely: running `tests/test_lang.py`
together with `tests/test_gates.py::TestParseFailureGate` under xdist
intermittently fails the pre-existing, unmodified
`test_no_parse_failures_is_clean`. Filed rather than silently patched
here or expanded into.

Filed: T-0926 (partial_parse_files() module-global state leaks
across tests that call build_graph directly -- PARSE002 flakiness)

Gates: `frob check --ticket T-0905` clean across all five stage groups
(lint/static/gates-fast/gates-native/gates-security), 0 errors in each
after the fixes above; no waivers needed.
