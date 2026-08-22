## Done report

Disposition per coordinator's own independent measurement (`frob check
--json` via `scripts/check_summary.py`, taken shortly before T-2034
landed): the SAME 6 identities this ticket filed were already present
on the tree before T-2034's commit -- 5 of them (both F401s, ARCH001+
ARCH103 on `_query.py`, ARCH001 on `_rapid_sweep.py`) are pre-existing
residue the rolling baseline had not recorded yet, not something T-2034
introduced. Only DRIFT002 on `_rapid_sweep.py` was genuinely new (my own
`frob:tests` directives on `_normalize_identity_file` outran the tests
that satisfy them by one commit) -- fixed directly: added
`TestNormalizeIdentityFile` (3 tests) to `tests/unit/test_rapid_sweep.py`,
confirmed `frob check --only drift` now reports zero DRIFT002 findings
for this file.

Read on the attribution-vs-filing question: NOT a defect, and I did not
file it. `_partition_findings_by_attribution`'s job (T-1690) is
narrowly "does this finding trace to a commit whose ticket is still
open" -- suppressing it there means "already tracked elsewhere, do not
re-file." UNATTRIBUTED does not mean "not new"; it means "no batch
commit's touched symbols reach this finding," which is exactly the
correct, conservative disposition for genuinely pre-existing residue
the rolling baseline never captured (T-1684's own stated job, not
attribution's). Filing UNATTRIBUTED findings is `_file_regression_
ticket`'s documented default behavior, not a gap in it -- the actual
defect here was narrower and specific to this land (the baseline
comparison point), not a design flaw in how attribution and filing
compose.

### Changed
```
 src/frob/app/ticket_runner/_rapid_sweep.py |  40 +++++++++
 tests/unit/test_rapid_sweep.py             | 135 +++++++++++++++++++++++++++++
 tickets/T-2030/ticket.md                   |  16 +++-
 tickets/T-2038/ticket.md                   |   8 +-
 4 files changed, 196 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestNormalizeIdentityFile::test_absolute_under_root_becomes_relative` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestNormalizeIdentityFile::test_already_relative_is_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestNormalizeIdentityFile::test_absolute_outside_root_falls_back_unchanged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@src/frob/app/ticket_runner/_query.py, F401@/home/logan/projects/frob/.claude/worktrees/sweep-drop-fix/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/sweep-drop-fix/tests/unit/test_tickets_evidence_only_scope.py, SELFAUDIT001@design
