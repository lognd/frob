---
id: T-0768
title: 'ticket CLI: quiet diagnostic logger noise (gitio/tickets DEBUG-INFO) by default,
  -v restores'
state: done
kind: ux
origin: human
created: '2026-07-22'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/app/config.py
- src/frob/__main__.py
- src/frob/logging/quiet.py
- src/frob/logging/__init__.py
- pyproject.toml
- .frob-release.json
- uv.lock
- tests/test_ticket_runner_quiet.py
- tests/unit/test_logging_quiet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: pyproject.toml
  reason: REL001 minor bump + stamp artifacts for new public logger_levels API
  actor: logan
  at: '2026-07-22'
- op: add
  glob: .frob-release.json
  reason: REL001 minor bump + stamp artifacts for new public logger_levels API
  actor: logan
  at: '2026-07-22'
- op: add
  glob: uv.lock
  reason: REL001 minor bump + stamp artifacts for new public logger_levels API
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/test_ticket_runner_quiet.py
  reason: evidence tests for the dispatch clamp and logger_levels helper
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/unit/test_logging_quiet.py
  reason: evidence tests for the dispatch clamp and logger_levels helper
  actor: logan
  at: '2026-07-22'
evidence:
- tests/test_ticket_runner_quiet.py::TestDiagnosticLogCtx::test_default_clamps_frob_tree_but_pins_runner_output
- tests/test_ticket_runner_quiet.py::TestDiagnosticLogCtx::test_verbose_skips_the_clamp
- tests/unit/test_logging_quiet.py::TestLoggerLevels::test_sets_and_restores_mapped_levels
designated_repro_test: null
acceptance:
- text: GIVEN frob ticket list at default verbosity WHEN it runs THEN no gitio/tickets
    DEBUG or INFO diagnostic lines appear while ticket rows still print; GIVEN frob
    ticket -v list THEN diagnostic INFO/DEBUG lines are restored
  evidence:
  - tests/test_ticket_runner_quiet.py::TestDiagnosticLogCtx::test_default_clamps_frob_tree_but_pins_runner_output
  - tests/test_ticket_runner_quiet.py::TestDiagnosticLogCtx::test_verbose_skips_the_clamp
  - tests/unit/test_logging_quiet.py::TestLoggerLevels::test_sets_and_restores_mapped_levels
threat: null
component: null
---
User request 2026-07-22: frob ticket list is drowned in gitio: spawning/returncode DEBUG lines and tickets: loader INFO chatter. Those lines are already DEBUG/INFO -- the stdout handler defaults to DEBUG and only frob check applies the T-0202 stdout_log_level quieting. But ticket CLI OUTPUT itself is _log.info on the runner logger, so a handler-level quiet would swallow the listing. Fix: per-logger overrides -- during ticket dispatch clamp logger frob to WARNING and pin frob.app.ticket_runner to INFO (its output channel), restored after; add a generic logger_levels context manager to frob.logging.quiet as the one shared home; add frob ticket -v (count) to skip the clamp like check -v. WARNING+ lines (stale-lease, over-broad-scope) still show.