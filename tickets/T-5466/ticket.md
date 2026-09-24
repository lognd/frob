---
id: T-5466
title: Scaffold DX generated logging integration test fails capsys assertion
state: queued
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while draining CI run 35951365410 (dev 9e0c89bb19). Failing (ubuntu +
macos, both node ids share one root cause):
- tests/system/test_scaffold_dx.py::test_python_toolchain_scaffold_passes_check_immediately[python-tool]
- tests/system/test_scaffold_dx.py::test_hyphenated_name_scaffold_installs_and_console_script_runs

Both scaffold a fresh project and run ITS OWN generated pytest suite as a
subprocess acceptance check; the generated suite fails one test:
tests/integration/test_logging_integration.py::test_get_logger_end_to_end_emits_a_configured_record
asserts a log line appears in capsys.readouterr() but it only shows up in
the pytest-captured stdout section, not capsys -- consistent with the
scaffolded project's logging config.toml building a StreamHandler bound to
the real sys.stdout at dictConfig time rather than the live stream capsys
redirects per-test.

Fix belongs in the scaffold project template under src/frob/scaffold/ (the
generated logging config or its accompanying test) -- not narrowed to the
exact template file in this drain pass.
