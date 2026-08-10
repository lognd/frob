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

## Done report

The fix itself (tests/conftest.py's autouse _neutralize_inherited_color_env
fixture, deleting FORCE_COLOR/NO_COLOR before every test) was already
landed and bound to T-1586 -- found already in place at ticket-start,
not something this ticket's own work needed to (re)implement. What was
genuinely missing, matching the ticket text's own explicit ask ("Needs a
regression test asserting a spawned CLI produces escape-free output with
FORCE_COLOR set in the parent env"), was that regression test -- added as
tests/unit/test_conftest_color_env.py:

- test_force_color_and_no_color_are_absent_from_this_process_env: direct
  proof the fixture ran.
- test_spawned_cli_produces_escape_free_output_despite_ambient_shell: a
  real `frob ticket list` subprocess (spawned with the default inherited
  environment, exactly how a typical test-authored subprocess call works)
  produces zero ANSI escapes.
- test_explicit_force_color_in_child_env_still_colors: counter-proof --
  passing FORCE_COLOR explicitly via the child's own env= still colors,
  confirming the clean output above is caused by the fixture's cleanup,
  not by `frob ticket list` being incapable of coloring at all.

Two capability-declaration errors from adding a new test file that spawns
git/frob subprocesses and reads os.environ container-membership:
SELFAUDIT001 (exec/fs.write/env.read not declared for tests/unit/
test_conftest_color_env.py on the `testsuite` design node -- fixed by
appending the file to the existing exec/fs.write clauses and adding a new
env.read clause, design/frob.strata) and WIRE001 (the private
_make_ticket_project helper needed a permanent="true" waiver, same T-1592
precedent as every other per-file-only test fixture in this repo).

docs/modules/logging.md (declared scope) needed no change -- it already
documents should_color's NO_COLOR/FORCE_COLOR precedence; this ticket adds
test coverage for an already-implemented isolation fixture, not new
documented behavior.

### Changed
```
 tickets/T-1586/ticket.md | 40 +++++++++++++++++++++++++++++++++++++++-
 1 file changed, 39 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_conftest_color_env.py::TestConftestColorEnvIsolation::test_force_color_and_no_color_are_absent_from_this_process_env` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_color_env.py::TestConftestColorEnvIsolation::test_spawned_cli_produces_escape_free_output_despite_ambient_shell` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_color_env.py::TestConftestColorEnvIsolation::test_explicit_force_color_in_child_env_still_colors` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 695 warning(s), 728 waived
- error-findings: none (measured, zero errors)
