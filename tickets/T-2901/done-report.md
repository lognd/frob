## Done report

Premise: reproduced exactly as ticketed. frob.graph.callgraph's
_called_names recognizes a call only as "identifier immediately followed
by (", which never matches bash's bare-word invocation syntax. Verified
with a manual build_call_graph run before touching code: a bash script
with a real function call resolved zero call edges.

Changed:
- src/frob/graph/callgraph.py: _BASH_STATEMENT_BOUNDARY_TOKENS (real bash
  grammar terminals: ; { } ( && || | & do then else elif fi done esac in
  if while until) + _BASH_RESERVED_WORDS (excluded from candidacy) +
  _bash_called_names (bare word immediately after a boundary token, or at
  body start, excluding an assignment LHS via the "next token is =" check).
  _called_names_from_sym now accepts an optional `path`, derives language
  via frob.lang.language_for_extension, and unions in _bash_called_names
  only for bash files -- every other language's resolution is byte-for-
  byte unchanged (path=None or non-bash path is a no-op). _referenced_names
  gained the same optional, ignored `path` param so _resolve_edges's loop
  can pass it uniformly to whichever name_extractor it holds.
- tests/test_graph.py: TestCallGraph gained 4 tests -- brace-adjacent call
  (must-fire/repro), semicolon+pipe+if-adjacent calls, assignment is NOT
  a call (must-stay-quiet), and newline-only separation stays a documented
  miss (must-stay-quiet, guards the known limitation from silently
  "fixing" into something wrong later).

What this does NOT close: the dominant "one command per line, no ;" bash
idiom has no token at all marking the statement boundary (tree-sitter
emits no leaf for whitespace/newlines) -- structurally unrecoverable from
body_tokens without a RawSymbol schema change, which is out of this
ticket's src/frob/graph/callgraph.py-only scope. Did NOT touch frob.lang.
_support's bash call_graph KNOWN_GAP declaration (out of scope, a
different file) -- it remains an honest KNOWN_GAP because full bash call
resolution is still not achieved, only a real, measurable subset (semicolon/
pipe/and-or/control-flow-adjacent calls) newly recognized.

Evidence: TestCallGraph's 4 new tests, all passing.
Gates: gate:SCOPE and gate:FMT (the two --ticket actually scopes) clean;
gate:COV shows 0 COV002 on my new symbols (all under frob:ticket T-2901)
and 0 new COV006 findings after retargeting frob:tests to build_call_graph
(the directly-called public entrypoint, matching every pre-existing test
in this class -- COV006's static reachability cannot see through the
name_extractor indirection _resolve_edges already used before this ticket).
BUG002 repro test-first order verified for real: test committed alone
first (abb6fcd0f), confirmed FAILING against the pre-fix code, THEN the
fix committed (d1c6f2298) -- frob ticket evidence --designate-repro
confirms FAILED_AT_PARENT against abb6fcd0f.

### Changed
```
 src/frob/graph/callgraph.py | 121 ++++++++++++++++++++++++++++++++++++++++++--
 tests/test_graph.py         |  97 +++++++++++++++++++++++++++++++++++
 tickets/T-2901/ticket.md    |   7 ++-
 3 files changed, 219 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/test_graph.py::TestCallGraph::test_build_call_graph_resolves_a_bash_bare_word_call_after_brace` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCallGraph::test_build_call_graph_resolves_bash_calls_after_semicolon_pipe_and_if` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCallGraph::test_build_call_graph_does_not_treat_bash_assignment_as_a_call` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCallGraph::test_build_call_graph_bash_newline_only_separation_is_a_known_gap` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 97 error(s), 2876 warning(s), 876 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV003@tickets/T-3223, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/clean/_core.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@src/frob/app/ticket_runner/_land_cmd.py, OPAQUE001@tests/test_vet_capability.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2901, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py, unresolved-attribute@scripts/fleet_status.py, unresolved-attribute@tests/system/test_fleet_status_ground_truth.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
