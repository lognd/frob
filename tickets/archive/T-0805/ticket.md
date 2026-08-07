---
id: T-0805
title: 'security: evidence-command runner spawns with shell=True on repo-writable
  ticket YAML input'
state: done
kind: security
origin: auditor
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/__init__.py
- tests/test_tickets_evidence_cli.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_shell_metacharacters_do_not_reach_a_shell
- tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_command_substitution_is_not_expanded
- tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_malformed_quoting_fails_cleanly_instead_of_shelling_out
- tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_exec_kill_switch_stops_evidence_commands
designated_repro_test: null
acceptance:
- text: 'GIVEN a cmd: evidence entry WHEN _run_evidence_command executes it THEN it
    runs without shell=True (argv form or an explicitly justified sanctioned shell
    path with input validation) and through the exec guard; a test proves shell metacharacters
    in a crafted evidence command do not reach a shell'
  evidence:
  - tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_shell_metacharacters_do_not_reach_a_shell
  - tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_command_substitution_is_not_expanded
  - tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_malformed_quoting_fails_cleanly_instead_of_shelling_out
  - tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_exec_kill_switch_stops_evidence_commands
threat: elevation-of-privilege
component: null
---
Split out of T-0803 per the T-0778 reviewer: tickets/__init__.py::_run_evidence_command runs caller-supplied commands from ticket YAML (repo-writable by every agent/tool) with shell=True -- injection-adjacent surface that must not ride a medium wiring ticket. Note evidence commands are a sanctioned feature (T-0215) so the fix must preserve legitimate cmd evidence (shlex.split argv execution or documented constrained shell) while removing raw shell interpolation, and wire through guarded_subprocess_run (T-0778).