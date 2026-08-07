---
id: T-1147
title: 'daemon: reconcile frob check --delta CLI payload with frob_check_delta RPC
  (T-1128 remainder)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/serve/_tools.py
- src/frob/app/check_runner.py
- docs/modules/serve.md
- tests/test_serve.py
- tests/test_app_daemon_proxy.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_serve.py
  reason: 'Widening frob_check_delta''s payload shape (the ticket''s own core change)

    breaks/needs new coverage in the existing unit tests

    (tests/test_serve.py::TestCheckDelta) and needs a new subprocess-vs-

    subprocess differential-parity test proving the daemon-served and

    in-process --only gates --delta --json answers match

    (tests/test_app_daemon_proxy.py::TestDifferentialParity), the T-1093/

    T-1106/T-1128 precedent location for exactly this kind of proof.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_app_daemon_proxy.py
  reason: 'Widening frob_check_delta''s payload shape (the ticket''s own core change)

    breaks/needs new coverage in the existing unit tests

    (tests/test_serve.py::TestCheckDelta) and needs a new subprocess-vs-

    subprocess differential-parity test proving the daemon-served and

    in-process --only gates --delta --json answers match

    (tests/test_app_daemon_proxy.py::TestDifferentialParity), the T-1093/

    T-1106/T-1128 precedent location for exactly this kind of proof.

    '
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_serve.py::TestCheckDelta::test_check_result_matches_only_gates_delta_cli_shape
- tests/test_serve.py::TestCheckDelta::test_delta_against_fresh_baseline_is_empty
- tests/test_app_daemon_proxy.py::TestDifferentialParity::test_check_delta_gates_only_json_daemon_matches_in_process
designated_repro_test: null
threat: null
component: null
---
T-1128 wired frob_graph_query/frob_doable_tickets/frob_run_touched_tests
through the daemon proxy (each _tools.py counterpart extended to match the
CLI's own --json shape field-for-field) but left frob_check_delta
unwired: it investigated the shape and found a genuine mismatch, not a
reconcilable one.

frob check --delta's CLI JSON payload is _run_all_stages's full
multi-tool CheckResult (ruff/ty/arch/cycle/dup/bind/exports/deploy-stage
ToolResults, gates among them) -- --delta itself only filters the ONE
gates ToolResult inside that larger payload
(check_runner._dispatch_check_python's delta=cfg.check_delta kwarg
threads into run_check, not into ruff/ty/arch/etc). frob_check_delta's
RPC (src/frob/serve/_tools.py) answers only the gates-violations-delta
question in isolation, structurally narrower than what
`frob check --delta --json` prints.

Two candidate directions, either judged out of scope for a plain
"CLI payload shape reconciliation" ticket:
1. Extend frob_check_delta to run the entire check pipeline (all
   non-gate tool stages too), not just gates -- a much larger change than
   a payload-shape fix, and duplicates check_runner.py's own multi-tool
   dispatch logic server-side.
2. Detect, CLI-side, the narrow all-gates-only invocation (every
   --skip-<tool> flag set except gates) and proxy only then, printing a
   CLI-shaped wrapper around the RPC's narrower delta payload for that
   one case.

Investigate which direction (or a third) is worth taking, and implement
it. Scope: src/frob/serve/_tools.py, src/frob/app/check_runner.py,
docs/modules/serve.md.