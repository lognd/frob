---
id: T-3028
title: frob check CHECK001 unknown-project-type fires before the lease-pin refusal
  in a git-worktree with no pyproject.toml
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_check.py::TestDetectProjectType::test_nested_py_file_no_root_marker_is_python
- tests/unit/test_check.py::TestDetectProjectType::test_nested_cpp_source_still_wins_over_absent_python
- tests/system/test_cli_check.py::TestCheckTicketLeasePinRefusal::test_ticket_lease_recorded_elsewhere_refuses
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while root-causing T-3019 (spurious REF001/PRE001/SCOPE001 on a
clean project). tests/system/test_cli_check.py::TestCheckTicketLeasePinRefusal::test_ticket_lease_recorded_elsewhere_refuses
fails on unmodified main (independently of T-3019's fix): a second linked
git worktree with no pyproject.toml resolves to project type "unknown"
(CHECK001) BEFORE `frob check --ticket <id>` ever reaches the lease-pin
collision check, so the test's expected "frob ticket start" refusal text
never appears -- the command still exits 1, but for the wrong, unrelated
reason.

Repro: build a main repo + tickets.md + one committed .py file (no
pyproject.toml at all), `frob ticket start T-0001 --foreground`, add a
second linked `git worktree`, run `frob check . --ticket T-0001 --only
gates` from it -- get `CHECK001: unknown project type: 'unknown'` instead
of the ticket-lease-pin refusal.

Out of T-3019's declared scope (src/frob/gates/_refs.py,
src/frob/check/_python.py) -- this is project-type detection order in
src/frob/check/__init__.py's dispatch path, a different module and a
different root cause than the REF001/PRE001/SCOPE001 rules T-3019 owns.