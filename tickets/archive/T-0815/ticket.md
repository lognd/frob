---
id: T-0815
title: 'app: sweep --json runners for guard-log stdout pollution (mutate and fleet
  already emit spawn DEBUG into JSON payloads)'
state: done
kind: bug
origin: auditor
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/mutate_runner.py
- src/frob/app/fleet_runner.py
- tests/integration/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_json_output_is_clean
- tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_human_mode_still_shows_diagnostics
- tests/integration/test_fleet_integration.py::TestFleetIntegrationJson::test_fleet_status_json_is_clean
- tests/integration/test_gitlog.py::TestGitlogJson::test_json_valid
designated_repro_test: null
acceptance:
- text: GIVEN every runner module with a json flag whose payload path can reach guarded_subprocess_run
    WHEN the json mode runs THEN stdout parses as clean JSON (conditional quiet_stdout_logs
    like xref_runner) and an integration test parses the full stdout per runner; GIVEN
    human mode THEN diagnostic lines still appear
  evidence:
  - tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_json_output_is_clean
  - tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_human_mode_still_shows_diagnostics
  - tests/integration/test_fleet_integration.py::TestFleetIntegrationJson::test_fleet_status_json_is_clean
threat: null
component: null
---
T-0803 reviewer finding: the exec guard now DEBUG-logs every spawn, and the
stdout handler defaults to DEBUG, so any --json runner spawning through the
guard pollutes its payload. gitlog_runner was fixed in T-0803
(unconditionally -- align it to the conditional xref pattern in this
sweep); mutate_runner and fleet_runner are polluted TODAY. Sweep every
runner with a _json flag, apply the conditional quiet_stdout_logs pattern
(quiet when json, nullcontext otherwise), and lock each with a
json.loads-of-full-stdout integration test.