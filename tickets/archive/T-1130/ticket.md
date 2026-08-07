---
id: T-1130
title: 'tickets: ticket new/drop/fail auto-commit their ledger transition on main
  (parity with T-1054 start)'
state: done
kind: ux
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_tickets.py
- src/frob/app/config.py
- src/frob/_cli_parsers/_ticket.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_close_cmd.py
- docs/modules/tickets.md
- tests/test_ticket_leases.py
- docs/modules/app.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/config.py
  reason: 'T-1130''s acceptance criterion (new/drop/fail auto-commit their ledger
    transition on main, with an opt-out flag) requires: config.py for the new --no-commit
    AppConfig field, _cli_parsers/_ticket.py to register the flag on the new/drop/fail
    subparsers, ticket_runner/_new.py and _close_cmd.py (the CLI handlers for new/drop/fail)
    to call the commit helper, docs/modules/tickets.md per playbook section 6'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/_cli_parsers/_ticket.py
  reason: 'T-1130''s acceptance criterion (new/drop/fail auto-commit their ledger
    transition on main, with an opt-out flag) requires: config.py for the new --no-commit
    AppConfig field, _cli_parsers/_ticket.py to register the flag on the new/drop/fail
    subparsers, ticket_runner/_new.py and _close_cmd.py (the CLI handlers for new/drop/fail)
    to call the commit helper, docs/modules/tickets.md per playbook section 6'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: 'T-1130''s acceptance criterion (new/drop/fail auto-commit their ledger
    transition on main, with an opt-out flag) requires: config.py for the new --no-commit
    AppConfig field, _cli_parsers/_ticket.py to register the flag on the new/drop/fail
    subparsers, ticket_runner/_new.py and _close_cmd.py (the CLI handlers for new/drop/fail)
    to call the commit helper, docs/modules/tickets.md per playbook section 6'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/app/ticket_runner/_close_cmd.py
  reason: 'T-1130''s acceptance criterion (new/drop/fail auto-commit their ledger
    transition on main, with an opt-out flag) requires: config.py for the new --no-commit
    AppConfig field, _cli_parsers/_ticket.py to register the flag on the new/drop/fail
    subparsers, ticket_runner/_new.py and _close_cmd.py (the CLI handlers for new/drop/fail)
    to call the commit helper, docs/modules/tickets.md per playbook section 6'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/tickets.md
  reason: 'T-1130''s acceptance criterion (new/drop/fail auto-commit their ledger
    transition on main, with an opt-out flag) requires: config.py for the new --no-commit
    AppConfig field, _cli_parsers/_ticket.py to register the flag on the new/drop/fail
    subparsers, ticket_runner/_new.py and _close_cmd.py (the CLI handlers for new/drop/fail)
    to call the commit helper, docs/modules/tickets.md per playbook section 6'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_ticket_leases.py
  reason: commit_start_transition's own T-1054 tests already live in tests/test_ticket_leases.py;
    commit_ticket_ledger_change (T-1130's generalization of the same add-and-commit
    primitive) belongs alongside them, not duplicated into test_tickets.py
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/app.md
  reason: 'AFFECT001: AppConfig (docs/modules/app.md#config) changed (new ticket_no_commit
    field for --no-commit); documenting it there per this doc''s own existing per-field-addition
    convention (T-1069/T-1004 precedent paragraphs)'
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_commits_dirty_ledger_with_given_message
- tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_no_op_when_ledger_already_clean
- tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_no_commit_flag_skips_entirely_even_when_dirty
- tests/test_ticket_leases.py::TestNewDropFailAutoCommit::test_new_auto_commits_the_filed_block
- tests/test_ticket_leases.py::TestNewDropFailAutoCommit::test_new_no_commit_leaves_ledger_dirty
- tests/test_ticket_leases.py::TestNewDropFailAutoCommit::test_drop_auto_commits_the_state_change
- tests/test_ticket_leases.py::TestNewDropFailAutoCommit::test_fail_auto_commits_the_failure_log_and_requeue
designated_repro_test: null
acceptance:
- text: GIVEN a coordinator files, drops, or fails a ticket on main WHEN the verb
    completes THEN the ledger change is committed automatically (with an opt-out flag),
    so a subsequent agent dispatch or land preflight can never hit uncommitted coordinator
    ledger state
  evidence:
  - tests/test_ticket_leases.py::TestNewDropFailAutoCommit::test_new_auto_commits_the_filed_block
threat: null
component: null
---
T-1054 made ticket start auto-commit its transition after DirtyMain incidents; new/drop/fail still leave tickets.md dirty and 'commit before dispatching' is coordinator memory (bit the T-1018 agent once; the playbook carries it as a must-remember). Same pattern, remaining verbs. Worktree-side behavior unchanged (worktree ledger edits reconcile at land).