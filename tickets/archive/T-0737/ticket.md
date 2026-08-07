---
id: T-0737
title: 'ticket CLI: --body-file/--acceptance-file/--reason-file variants so prose
  never rides the shell'
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
- docs/modules/tickets.md
- docs/guides/agent-playbook.md
- tests/unit/test_ticket_file_flags.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_file_flags.py
  reason: T-0737 needs a dedicated test file for the new --body-file/--acceptance-file/--reason-file
    CLI flags, mirroring the tests/unit/ home for other ticket_runner CLI tests
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/test_ticket_file_flags.py::TestNewBodyFile::test_body_file_round_trips_byte_exact
- tests/unit/test_ticket_file_flags.py::TestNewBodyFile::test_body_and_body_file_together_errors_cleanly
- tests/unit/test_ticket_file_flags.py::TestNewBodyFile::test_unreadable_body_file_errors_cleanly
- tests/unit/test_ticket_file_flags.py::TestNewAcceptanceFile::test_blank_line_separated_blocks_become_criteria
- tests/unit/test_ticket_file_flags.py::TestNewAcceptanceFile::test_one_per_line_when_no_blank_lines
- tests/unit/test_ticket_file_flags.py::TestNewAcceptanceFile::test_acceptance_and_acceptance_file_together_errors_cleanly
- tests/unit/test_ticket_file_flags.py::TestScopeReasonFile::test_reason_file_round_trips_byte_exact
- tests/unit/test_ticket_file_flags.py::TestScopeReasonFile::test_reason_and_reason_file_together_errors_cleanly
- tests/unit/test_ticket_file_flags.py::TestScopeReasonFile::test_neither_reason_nor_reason_file_errors_cleanly
designated_repro_test: null
acceptance:
- text: GIVEN a body file containing backticks, quotes, and dollar signs WHEN frob
    ticket new --body-file runs THEN the ledger body matches the file byte-for-byte
  evidence:
  - tests/unit/test_ticket_file_flags.py::TestNewBodyFile::test_body_file_round_trips_byte_exact
  - tests/unit/test_ticket_file_flags.py::TestNewBodyFile::test_body_and_body_file_together_errors_cleanly
  - tests/unit/test_ticket_file_flags.py::TestNewBodyFile::test_unreadable_body_file_errors_cleanly
  - tests/unit/test_ticket_file_flags.py::TestNewAcceptanceFile::test_blank_line_separated_blocks_become_criteria
  - tests/unit/test_ticket_file_flags.py::TestNewAcceptanceFile::test_one_per_line_when_no_blank_lines
  - tests/unit/test_ticket_file_flags.py::TestNewAcceptanceFile::test_acceptance_and_acceptance_file_together_errors_cleanly
  - tests/unit/test_ticket_file_flags.py::TestScopeReasonFile::test_reason_file_round_trips_byte_exact
  - tests/unit/test_ticket_file_flags.py::TestScopeReasonFile::test_reason_and_reason_file_together_errors_cleanly
  - tests/unit/test_ticket_file_flags.py::TestScopeReasonFile::test_neither_reason_nor_reason_file_errors_cleanly
threat: null
component: null
---
Shell-substitution hazard, 4 field occurrences 2026-07-22 (T-0627, T-0697, T-0735/T-0736 bodies all lost backticked fragments to command substitution when passed inline through bash): long prose should never ride the shell. Add file-input variants mirroring done-report --why-file: frob ticket new --body-file PATH (and --acceptance-file PATH, one criterion per block/line), frob ticket scope --reason-file, frob ticket review already takes --findings-file (precedent). Inline --body stays for short text. Update the agent playbook to route all multi-sentence ticket prose through the file variants. The coordinator additionally runs a PreToolUse hook blocking backtick-in-double-quoted-flag commands; the file variants make the hazard structurally unreachable for agents too.