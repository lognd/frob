---
id: T-1855
title: Disclose implicit CLI-wiring scope in ticket show and CrossTicketLeakage refusal
state: done
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_query.py
- src/frob/_cli_parsers/**
- src/frob/tickets/_scope.py
- src/frob/app/ticket_runner/_mutate.py
- tests/test_tickets_scope_mutation.py
- tests/test_tickets_acceptance.py
- tickets/T-1860/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_scope.py
  reason: grant-on-use + scope--remove warning logic lives in mutate_scope/_scope()
    handler, not the 3 originally-cited files
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: grant-on-use + scope--remove warning logic lives in mutate_scope/_scope()
    handler, not the 3 originally-cited files
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_tickets_scope_mutation.py
  reason: test coverage for T-1855's new scope-disclosure/grant-on-use/remove-warning
    behavior
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_tickets_acceptance.py
  reason: test coverage for T-1855's new scope-disclosure/grant-on-use/remove-warning
    behavior
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1860/**
  reason: T-1855 filed this draft follow-up itself; its own shard needs to be in scope
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_tickets_scope_mutation.py::TestScopeCli::test_cli_remove_still_implicit_warns
- tests/test_tickets_scope_mutation.py::TestScopeCli::test_cli_remove_genuinely_free_no_warning
- tests/test_tickets_scope_mutation.py::TestScopeClaimReasonAndGrantOnUse::test_declared_path_is_declared
- tests/test_tickets_scope_mutation.py::TestScopeClaimReasonAndGrantOnUse::test_implicit_cli_wiring_path_is_flagged
- tests/test_tickets_scope_mutation.py::TestScopeClaimReasonAndGrantOnUse::test_unused_implicit_grant_not_explicitly_used
- tests/test_tickets_scope_mutation.py::TestScopeClaimReasonAndGrantOnUse::test_explicit_add_counts_as_used
- tests/test_tickets_acceptance.py::TestAcceptanceAmendmentsSurfaced::test_show_renders_implicit_cli_wiring_scope
- tests/test_tickets_acceptance.py::TestAcceptanceAmendmentsSurfaced::test_show_omits_implicit_scope_when_fully_declared
designated_repro_test: null
threat: null
component: null
---
T-1848 narrowed the implicit FEATURE CLI-wiring grant in _models.py (CLI_WIRING_FILES: ticket_runner/** -> ticket_runner/__init__.py only), but that ticket's declared scope was only src/frob/tickets/_models.py, so it could not also: (1) disclose the effective (declared + implicit CLI-wiring) scope in 'frob ticket show'; (2) have the CrossTicketLeakage land refusal say WHY a file is claimed (implicit CLI-wiring rule vs declared scope); (3) make 'frob ticket scope --remove' refuse or warn when the removed glob is still covered implicitly. See T-1848's body for the full incident writeup and required behavior.