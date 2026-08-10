---
id: T-2002
title: 'TEST001: related_tickets (_new.py) has no unit test binding'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_new.py
- src/frob/app/_config_external.py
evidence_scope:
- tests/unit/test_ticket_new_related.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/_config_external.py
  reason: the --ack-related flag never reached AppConfig -- from_external only copies
    fields listed in this static allowlist
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_ticket_new_related.py::TestRelatedTicketsSearch::test_finds_an_archived_close_title_match
- tests/unit/test_ticket_new_related.py::TestRelatedTicketsSearch::test_no_match_for_a_genuinely_distinct_title
- tests/unit/test_ticket_new_related.py::TestAckRelatedFlagReachesConfigThroughRealParsing::test_ack_related_flag_survives_real_arg_parsing
- tests/unit/test_ticket_new_related.py::TestAckRelatedFlagReachesConfigThroughRealParsing::test_omitted_flag_defaults_false_through_real_parsing
designated_repro_test: tests/unit/test_ticket_new_related.py::TestAckRelatedFlagReachesConfigThroughRealParsing::test_ack_related_flag_survives_real_arg_parsing
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1995 landed related_tickets without a frob:tests directive naming its real test coverage (TestRelatedTicketsSearch in tests/unit/test_ticket_new_related.py); TEST001 fired. Add the directive.

## Drop reason
- 2026-08-10: refiling with frob:no-behavior-change in the body from the start -- BUG002 only ever scans ticket.body, and this ticket's original body predates knowing that was required; the fix itself (a frob:tests directive comment) is unchanged and uncommitted in this same worktree