---
id: T-0446
title: 'ticket scope-declaration gap: new subcommands require CLI-wiring files (__main__/config/ticket_runner)
  not in declared scope (T-0323 sibling)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/
- docs/
- tests/test_tickets.py
- tests/test_gates.py
- src/frob/gates/__init__.py
- pyproject.toml
- CHANGELOG.md
- uv.lock
- .frob-release.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets.py
  reason: T-0446 fix touches scope_matches (tests/test_tickets.py) plus the SCOPE001
    gate call site and its tests (src/frob/gates/__init__.py, tests/test_gates.py)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_gates.py
  reason: T-0446 fix touches scope_matches (tests/test_tickets.py) plus the SCOPE001
    gate call site and its tests (src/frob/gates/__init__.py, tests/test_gates.py)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/gates/__init__.py
  reason: T-0446 fix touches scope_matches (tests/test_tickets.py) plus the SCOPE001
    gate call site and its tests (src/frob/gates/__init__.py, tests/test_gates.py)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: T-0446 changed public API (scope_matches signature, new CLI_WIRING_FILES
    constant), requiring REL001 version bump per repo convention
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: T-0446 changed public API (scope_matches signature, new CLI_WIRING_FILES
    constant), requiring REL001 version bump per repo convention
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: T-0446 changed public API (scope_matches signature, new CLI_WIRING_FILES
    constant), requiring REL001 version bump per repo convention
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: frob release stamp writes this file as part of the REL001 bump for T-0446
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_tickets.py::TestScopeMatching::test_feature_kind_implies_cli_wiring_files_in_scope
- tests/test_tickets.py::TestScopeMatching::test_non_feature_kind_does_not_imply_cli_wiring_files
- tests/test_gates.py::TestScopePrework::test_scope001_feature_ticket_cli_wiring_files_implicitly_in_scope
- tests/test_gates.py::TestScopePrework::test_scope001_non_feature_ticket_cli_wiring_files_still_out_of_scope
designated_repro_test: null
threat: null
component: null
---
