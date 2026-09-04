---
id: T-3762
title: did-you-mean suggestion missing on Python 3.12 (Windows)
state: in-progress
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_root.py
- tests/unit/test_main_entry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Python 3.12 changed argparse invalid-choice message from quoted to unquoted choice list; _INVALID_CHOICE_RE only matches quoted form so suggestion is dropped on Python 3.12 (Windows CI). Confirmed via winrun. Fix regex to accept both forms. Affected tests: tests/unit/test_main_entry.py::TestDidYouMean::test_unknown_subcommand_suggests_closest, test_unknown_ticket_subcommand_suggests_closest