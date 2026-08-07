---
id: T-1525
title: 'coverage: user-facing frob coverage CLI verb + decide frob check auto-trigger
  for non-agent callers'
state: done
kind: feature
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/__main__.py
- src/frob/_cli_parsers/_misc.py
- src/frob/app/app.py
- src/frob/app/config.py
- src/frob/app/_config_external.py
- src/frob/app/coverage_runner.py
- docs/modules/cli.md
- tests/unit/test_main_entry.py
- tests/test_app_config.py
- tests/unit/test_coverage_runner.py
- src/frob/_cli_parsers/__init__.py
- README.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: CLI verb wiring needs Subcommand enum + config fields + runner + parser
    registration, not just __main__.py dispatch; declared scope predated the actual
    convention this repo uses (natives_runner precedent)
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/app/app.py
  reason: CLI verb wiring needs Subcommand enum + config fields + runner + parser
    registration, not just __main__.py dispatch; declared scope predated the actual
    convention this repo uses (natives_runner precedent)
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/app/config.py
  reason: CLI verb wiring needs Subcommand enum + config fields + runner + parser
    registration, not just __main__.py dispatch; declared scope predated the actual
    convention this repo uses (natives_runner precedent)
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/app/_config_external.py
  reason: CLI verb wiring needs Subcommand enum + config fields + runner + parser
    registration, not just __main__.py dispatch; declared scope predated the actual
    convention this repo uses (natives_runner precedent)
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/app/coverage_runner.py
  reason: CLI verb wiring needs Subcommand enum + config fields + runner + parser
    registration, not just __main__.py dispatch; declared scope predated the actual
    convention this repo uses (natives_runner precedent)
  actor: logan
  at: '2026-08-05'
- op: add
  glob: docs/modules/cli.md
  reason: CLI verb wiring needs Subcommand enum + config fields + runner + parser
    registration, not just __main__.py dispatch; declared scope predated the actual
    convention this repo uses (natives_runner precedent)
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/unit/test_main_entry.py
  reason: CLI verb wiring needs Subcommand enum + config fields + runner + parser
    registration, not just __main__.py dispatch; declared scope predated the actual
    convention this repo uses (natives_runner precedent)
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/test_app_config.py
  reason: CLI verb wiring needs Subcommand enum + config fields + runner + parser
    registration, not just __main__.py dispatch; declared scope predated the actual
    convention this repo uses (natives_runner precedent)
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/unit/test_coverage_runner.py
  reason: CLI verb wiring needs Subcommand enum + config fields + runner + parser
    registration, not just __main__.py dispatch; declared scope predated the actual
    convention this repo uses (natives_runner precedent)
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/_cli_parsers/__init__.py
  reason: re-export barrel for the new _add_coverage_parser builder, same pattern
    every existing parser follows
  actor: logan
  at: '2026-08-05'
- op: add
  glob: README.md
  reason: DOC005 requires the new frob coverage verb's README command-table row +
    updated count, same as every prior CLI-verb ticket (T-0864 precedent)
  actor: logan
  at: '2026-08-05'
evidence:
- tests/unit/test_coverage_runner.py::TestCoverageRunner::test_default_delegates_to_run_coverage_wait
- tests/unit/test_coverage_runner.py::TestCoverageRunner::test_full_calls_native_refresh_directly
- tests/unit/test_coverage_runner.py::TestCoverageRunner::test_run_failure_exits_nonzero
designated_repro_test: null
threat: null
component: null
---
T-1516/T-1205 acceptance[3]'s other half: native_coverage_refresh exists as a library function but has no CLI entrypoint (frob coverage / frob test --coverage). Also open: T-1205 acceptance[4] literally asks for auto-refresh inside any frob command whose gates need coverage data; frob check deliberately does not do this for a dispatched worktree agent (FROB_AGENT=1, docs/guides/agent-playbook.md section 3b's foreground-timeout contract), but no decision has been made about whether a non-agent (human/CI) frob check invocation -- where that constraint does not apply -- should auto-trigger. Wire the CLI verb and make and document that decision.