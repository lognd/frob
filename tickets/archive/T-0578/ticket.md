---
id: T-0578
title: 'CLI vocabulary normalization + did-you-mean: --state vs --status, --why vs
  --body, consistent flags'
state: done
kind: ux
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_main_entry.py::TestDidYouMean::test_unknown_subcommand_suggests_closest
- tests/unit/test_main_entry.py::TestDidYouMean::test_unknown_ticket_subcommand_suggests_closest
- tests/unit/test_main_entry.py::TestDidYouMean::test_unrecognized_flag_suggests_closest_known_flag
- tests/unit/test_main_entry.py::TestDidYouMean::test_far_off_flag_gets_no_suggestion
- tests/unit/test_main_entry.py::TestVocabularyAliases::test_ticket_list_status_alias_sets_state_dest
- tests/unit/test_main_entry.py::TestVocabularyAliases::test_ticket_done_report_body_alias_sets_why_dest
designated_repro_test: null
threat: null
component: null
---
Observed misuse: frob ticket list --status (correct: --state), done-report --body (correct: --why). Normalize flag vocabulary across subcommands (one name per concept), add argparse suggestions on unknown flags/subcommands. Scope: src/frob/__main__.py, app/config.py, docs/commands/.