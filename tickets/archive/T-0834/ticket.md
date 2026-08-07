---
id: T-0834
title: 'ticket CLI: no kind editor; evidence-cmd runs from invoking cwd not --path'
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/tickets/__init__.py
- tests/test_ticket_evidence.py
- src/frob/app/config.py
- src/frob/__main__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/config.py
  reason: 'T-0834 needs new/kind AppConfig field and __main__.py subcommand parser
    wiring, same bootstrap precedent T-0411/priority and T-0454/component used for
    their own CLI additions (scope0323/0453/0455 lineage).

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/__main__.py
  reason: 'T-0834 needs new/kind AppConfig field and __main__.py subcommand parser
    wiring, same bootstrap precedent T-0411/priority and T-0454/component used for
    their own CLI additions (scope0323/0453/0455 lineage).

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_ticket_evidence.py::TestSetKind::test_updates_kind_field
- tests/test_ticket_evidence.py::TestSetKind::test_audit_trail_present
- tests/test_ticket_evidence.py::TestSetKind::test_terminal_state_matches_priority
- tests/test_ticket_evidence.py::TestKindCliInvalidKind::test_invalid_kind_refused
- tests/test_ticket_evidence.py::TestKindCliInvalidKind::test_kind_cli_changes_persisted_kind
- tests/test_ticket_evidence.py::TestEvidenceCmdCwd::test_relative_probe_only_succeeds_from_worktree
- tests/test_ticket_evidence.py::TestEvidenceCmdCwd::test_add_cmd_evidence_runs_against_ticket_path_worktree
- tests/test_ticket_evidence.py::TestEvidenceCmdCwd::test_failure_message_names_resolved_cwd
designated_repro_test: null
threat: null
component: null
---
Two coordinator frictions hit landing T-0833 (2026-07-23):

1. kind is not editable via CLI. `frob ticket priority/component/label`
   exist, but correcting a mis-filed kind (feature -> docs, needed
   because --evidence-cmd is docs-kind-only) required hand-editing the
   yaml block in tickets.md. Add `frob ticket kind <id> <kind>` with the
   same audit-trail treatment as priority changes.

2. `frob ticket evidence --evidence-cmd` runs COMMAND from the invoking
   process cwd, not from the ticket's --path worktree. A relative-path
   probe (grep over scope files) silently ran against the ROOT checkout
   and failed with a bare exit=1 and empty stderr tail; the workaround
   was an absolute-path cd inside the script. Run the command with
   cwd=<resolved --path> (matching where the evidence claim is about),
   and include the resolved cwd in the failure message.