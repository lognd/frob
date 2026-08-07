---
id: T-0568
title: 'frob ticket brief: generate the complete agent mission prompt for a ticket'
state: done
kind: feature
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_brief.py::TestParsePlaybookSections::test_parses_numbered_headings_only
- tests/test_tickets_brief.py::TestParsePlaybookSections::test_body_stops_at_next_heading_numbered_or_not
- tests/test_tickets_brief.py::TestParsePlaybookSections::test_empty_text_yields_no_sections
- tests/test_tickets_brief.py::TestLoadPlaybookSections::test_missing_file_returns_empty
- tests/test_tickets_brief.py::TestLoadPlaybookSections::test_reads_real_file
- tests/test_tickets_brief.py::TestInferVerifyCommands::test_scope_naming_tests_dir_is_used_directly
- tests/test_tickets_brief.py::TestInferVerifyCommands::test_matches_test_file_by_stem
- tests/test_tickets_brief.py::TestInferVerifyCommands::test_no_scope_yields_only_check_command
- tests/test_tickets_brief.py::TestGateBaselineSummary::test_missing_baseline
- tests/test_tickets_brief.py::TestGateBaselineSummary::test_present_baseline
- tests/test_tickets_brief.py::TestCurrentVersion::test_missing_pyproject_is_none
- tests/test_tickets_brief.py::TestCurrentVersion::test_reads_project_version
- tests/test_tickets_brief.py::TestBriefTicket::test_composes_full_briefing
- tests/test_tickets_brief.py::TestBriefTicket::test_unknown_ticket_not_found
- tests/test_tickets_brief.py::TestBriefCli::test_cli_prints_briefing
- tests/test_tickets_brief.py::TestBriefCli::test_cli_requires_id
designated_repro_test: null
threat: null
component: null
---
Coordinator wrote the same 400-word dispatch boilerplate ~30 times this session (playbook refs, scope, verify commands, land rules, honesty clauses). frob ticket brief T-XXXX should emit the full mission briefing: body+acceptance, scope with leases, the relevant playbook hard-rule sections, exact targeted verify commands for the area, current gate baseline, REL/land rules. Dispatch prompts collapse to two lines and prompt drift disappears. Scope: src/frob/app/ticket_runner.py, src/frob/tickets/, docs/modules/tickets.md.