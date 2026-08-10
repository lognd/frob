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
