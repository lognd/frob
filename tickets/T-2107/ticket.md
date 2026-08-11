---
id: T-2107
title: 'argparse suggests flags from a different subparser: ''unrecognized arguments:
  --set X (did you mean: --set?)'' names a flag the invoked subcommand does not have'
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
- src/frob/__main__.py
- tests/unit/test_main_entry.py
- tickets/T-2112/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/_argparse.py
  reason: 'correct scope: bug lives in frob.__main__._SuggestingArgumentParser, not
    the nonexistent _argparse.py'
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/app/__init__.py
  reason: 'correct scope: bug lives in frob.__main__._SuggestingArgumentParser, not
    the nonexistent _argparse.py'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/__main__.py
  reason: 'correct scope: bug lives in frob.__main__._SuggestingArgumentParser, not
    the nonexistent _argparse.py'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_main_entry.py
  reason: 'correct scope: bug lives in frob.__main__._SuggestingArgumentParser, not
    the nonexistent _argparse.py'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-2112/ticket.md
  reason: filing the follow-up ticket writes this file; SCOPE001 flags it same as
    any other new path
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_main_entry.py::TestDidYouMean::test_unrecognized_flag_suggestion_scoped_to_invoked_subcommand
- tests/unit/test_main_entry.py::TestDidYouMean::test_unrecognized_flag_error_shows_invoked_subcommand_usage
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
