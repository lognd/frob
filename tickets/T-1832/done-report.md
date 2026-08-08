## Done report

Added a paragraph to the "Deferred post-land sweep (rapid only, T-1684)"
section of docs/modules/tickets.md documenting `_staged_rapid_debt_ticket`
(T-1821): it reads the STAGED rapid-debt.jsonl blob directly, parses the
last line, and returns its own "ticket" field, so a DirtyMain refusal can
name "the sweep child working T-XXXX" instead of the generic "unattributed
sweep" text T-1755 introduced. Documents the "unattributed (cannot be
determined from staged content)" fallback for an unreadable/unparseable
blob, and why that refusal-to-guess matters (the T-1795/T-1799 incident).

Removed the AFFECT001 waiver T-1821 had left on describe_root_dirt in
src/frob/tickets/_land_git_ops.py now that the doc anchor it cited as a
follow-up is landed.

### Changed
```
 docs/modules/tickets.md           | 37 +++++++++++++++++++++++++++++++++++++
 src/frob/tickets/_land_git_ops.py |  3 ---
 tickets/T-1832/ticket.md          | 11 +++++++++++
 tickets/T-1878/done-report.md     | 28 ++++++++++++++++++++++++++++
 tickets/T-1878/ticket.md          |  2 ++
 5 files changed, 78 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_names_the_real_ticket_from_a_staged_rapid_debt_line` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_unattributed_when_the_true_author_cannot_be_determined` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 1 error(s), 1063 warning(s), 694 waived
- error-findings: PRE001@tickets/T-1832
