---
id: T-1586
title: 'test isolation: scrub inherited FORCE_COLOR/NO_COLOR in conftest'
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/conftest.py
- docs/modules/logging.md
- tests/unit/test_conftest_color_env.py
- tickets/T-1586/**
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_conftest_color_env.py
  reason: 'T-1586: the ticket''s own acceptance criterion (regression test for a spawned
    CLI subprocess) needs a new test file; own ticket dir needed for Done report'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1586/**
  reason: 'T-1586: the ticket''s own acceptance criterion (regression test for a spawned
    CLI subprocess) needs a new test file; own ticket dir needed for Done report'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/test_conftest_color_env.py
  reason: 'T-1586: the ticket''s own acceptance criterion (regression test for a spawned
    CLI subprocess) needs a new test file; own ticket dir needed for Done report'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1586/**
  reason: 'T-1586: the ticket''s own acceptance criterion (regression test for a spawned
    CLI subprocess) needs a new test file; own ticket dir needed for Done report'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: 'T-1586: the new spawned-CLI regression test''s capabilities (exec/fs.write/env.read)
    need declaring on the testsuite design node'
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/test_conftest_color_env.py::TestConftestColorEnvIsolation::test_force_color_and_no_color_are_absent_from_this_process_env
- tests/unit/test_conftest_color_env.py::TestConftestColorEnvIsolation::test_spawned_cli_produces_escape_free_output_despite_ambient_shell
- tests/unit/test_conftest_color_env.py::TestConftestColorEnvIsolation::test_explicit_force_color_in_child_env_still_colors
designated_repro_test: null
threat: null
component: null
---
should_color honors FORCE_COLOR and NO_COLOR, and a CLI subprocess a test spawns inherits the whole environment. A shell exporting FORCE_COLOR=3 (Claude Code and several CI images do) embeds ANSI escapes in every CLI output a test asserts on: 5 system tests failed here purely from the ambient shell while the same commit passes elsewhere. An autouse conftest fixture now deletes both per test (delete, not force NO_COLOR, so color-path tests can still monkeypatch either one). Needs a regression test asserting a spawned CLI produces escape-free output with FORCE_COLOR set in the parent env.