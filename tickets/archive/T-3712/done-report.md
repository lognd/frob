## Done report

Made T-2691's DOC006 regression self-contained: the live tickets/T-2691/ticket.md
that test_real_ticket_file_not_flagged read was archived to
tickets/archive/T-2691/ticket.md this session, breaking the test on both POSIX
CI legs. Replaced the live-file read with an inline `_TICKET_2691_BODY` string
constant reproducing T-2691's actual post-T-2697-fix prose verbatim (the future
verb quoted in prose rather than backtick-quoted as a live CLI invocation),
so the regression asserts DOC006's real behavior against a stable reproduction
instead of a ledger file that archiving can legitimately move. All 5 tests in
the file pass; frob test --base main passes; gates-fast/gates-native/
gates-security/lint/static all clean via --ticket T-3712 except pre-existing
DEPR006 (deprecated-baseline lock staleness, repo-wide, unrelated to this
ticket's scope).

### Changed
```
 tests/unit/test_ticket_2691_doc006.py | 58 +++++++++++++++++++++++++++++------
 tickets/T-3712/done-report.md         | 28 +++++++++++++++++
 tickets/T-3712/ticket.md              |  2 ++
 3 files changed, 79 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_2691_doc006.py::TestTicket2691Doc006Regression::test_real_ticket_file_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 4331 warning(s), 915 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json
