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
land_commit: null
---
T-1995 landed related_tickets without a frob:tests directive naming its real test coverage (TestRelatedTicketsSearch in tests/unit/test_ticket_new_related.py); TEST001 fired. Add the directive.

## Drop reason
- 2026-08-10: refiling with frob:no-behavior-change in the body from the start -- BUG002 only ever scans ticket.body, and this ticket's original body predates knowing that was required; the fix itself (a frob:tests directive comment) is unchanged and uncommitted in this same worktree

## Done report

Two fixes, both discovered while closing out T-1995's TEST001 residue: (1) added the missing frob:tests directive on related_tickets, and (2) a REAL bug found in the process -- --ack-related was silently dropped by AppConfig.from_external's static field-copy allowlist (src/frob/app/_config_external.py), so the CLI flag never worked end-to-end even though every T-1995 test passed (they all construct AppConfig directly, bypassing argparse). Added a real argparse-parsing regression test (TestAckRelatedFlagReachesConfigThroughRealParsing) that fails before the allowlist fix and passes after -- verified by hand (revert/restore via patch, no cross-branch checkout).

### Changed
```
 rapid-debt.jsonl                        |  4 ++++
 src/frob/app/ticket_runner/_new.py      |  2 ++
 tickets/T-2002/done-report.md | 20 ++++++++++++++++
 tickets/T-2002/ticket.md      | 41 +++++++++++++++++++++++++++++++++
 4 files changed, 67 insertions(+)
```

### Evidence
- `tests/unit/test_ticket_new_related.py::TestRelatedTicketsSearch::test_finds_an_archived_close_title_match` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_related.py::TestRelatedTicketsSearch::test_no_match_for_a_genuinely_distinct_title` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_related.py::TestAckRelatedFlagReachesConfigThroughRealParsing::test_ack_related_flag_survives_real_arg_parsing` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_related.py::TestAckRelatedFlagReachesConfigThroughRealParsing::test_omitted_flag_defaults_false_through_real_parsing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: DSL001@CHANGELOG.md, F401@/home/logan/projects/frob/.claude/worktrees/t1995-follow/tests/unit/test_tickets_evidence_only_scope.py
