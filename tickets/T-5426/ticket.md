---
id: T-5426
title: 'scaffold python-tool logging template: StreamHandler binds sys.stdout once
  per process, breaking pytest capsys isolation across tests'
state: queued
kind: bug
origin: human
created: '2026-09-23'
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
scope:
- src/frob/scaffold/data/shared/python/logging/logger.py.j2
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
Found while working T-5396 (distinct from T-5107's PYTHONPATH-leak diagnosis -- re-verified with a clean shell PYTHONPATH, the failure reproduces regardless): tests/system/test_scaffold_dx.py's scaffolded python-tool project fails its own nested pytest run at tests/integration/test_logging_integration.py::test_get_logger_end_to_end_emits_a_configured_record with 'integration smoke: hello' not found in capsys output, even though the Captured stdout call section shows the line WAS printed. Root cause: logger.py.j2's _init() runs logging.config.dictConfig ONCE per process (module-level _initialized flag), so the config.toml.j2-declared StreamHandler(stream="ext://sys.stdout") binds to whichever sys.stdout OBJECT is live the first time ANY test in the session calls get_logger() -- pytest's capsys fixture installs a NEW stdout-capture object per test, so only the first caller's own capsys sees the handler's writes; every later test's handler reference is stale and its capsys.readouterr() sees nothing, even though logging.info did run (visible in pytest's own '-- Captured log call --' section, a separate capture channel). Fix needs a StreamHandler that resolves sys.stdout live at write time (e.g. a small lazy-stream wrapper) rather than a config-time snapshot, or redesign _init()'s once-per-process caching to not defeat capsys isolation -- verify against a fresh scaffold + pytest run with >=2 tests exercising get_logger before declaring green, not just the single failing test in isolation (test order/count is exactly what triggers this).