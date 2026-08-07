---
id: T-1474
title: T-1360 footgun hook pollutes --json stdout with gitio log lines
state: done
kind: bug
origin: human
created: '2026-08-03'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/telemetry.py
- tests/test_telemetry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_telemetry.py
  reason: footgun detect_footguns/tree_hash test coverage lives here
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_telemetry.py::test_timed_call_records_event_and_returns_value
- tests/test_telemetry.py::test_record_cli_event_shape
- tests/test_telemetry.py::test_detect_footguns_flags_fast_exit1
- tests/system/test_cli_parse.py::test_pytest_json_exit_zero
- tests/test_telemetry.py::test_timed_call_does_not_leak_gitio_logs_onto_stdout
designated_repro_test: null
threat: null
component: null
---
The 2026-08-03 full-suite run has 117 FAILED tests, dominated by
json.decoder errors in tests/system/test_cli_*.py -- every `--json` CLI
command's stdout now carries trailing "gitio: spawning ('git', ...
'rev-parse', '--short', 'HEAD')..." log lines appended after the JSON
document.

Root cause: `frob.app.telemetry._finish_timed_call` (T-1360's own footgun
detection wiring) calls `detect_footguns(..., tree_hash_value=tree_hash(root))`
directly, NOT inside `quiet_stdout_logs()`. `tree_hash` spawns `git` via
`frob.gitio.run_argv`, whose module logger emits INFO-level lines that the
root logger's stdout handler (config.toml: DEBUG..WARNING routed to
stdout) prints immediately. Only the LATER `record_cli_event` call (which
also calls `tree_hash(root)` a second time) is wrapped in
`quiet_stdout_logs()` -- the earlier, unwrapped call in `_finish_timed_call`
leaks the gitio spawn log onto stdout, appended after the command's own
`--json` payload, corrupting it for any caller doing `json.loads(stdout)`.

T-1360's own design note (module docstring on `record_cli_event`) already
states the requirement that telemetry must be invisible on stdout -- the
detect_footguns call site was simply missed when quieting was added.