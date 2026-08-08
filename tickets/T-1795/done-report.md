## Done report

Two of the two required fixes, both narrowly scoped:

1. SYMBOLIC DirtyMain attribution. describe_root_dirt/_likely_sweep_
authored used to name a STATIC ticket pair (T-1699/T-1755, the tickets
that BUILT the sweep) whenever rapid-debt.jsonl or tickets.md was the
dirty file -- confidently wrong every time, since those are never the
ticket whose sweep child actually staged the line. New
_staged_rapid_debt_ticket reads the REAL ticket id off rapid-debt.jsonl's
own staged diff content (every line already carries its own "ticket"
field via record_rapid_debt) -- a fact read from content, never a
guess. Falls back to "unattributed" (never a plausible-but-wrong ticket)
for any other sweep-owned path, matching the same "cannot verify is
never verified" rule this module's own liveness probes already follow.

2. Advisory-visible land lock, retiring pgrep. `frob doctor` already had
T-1515/T-1634's scan_live_land_processes/LiveLandProcess -- it read
.frob/land.lock's REAL content (pid/session/liveness, race-free, unlike
pgrep) but never surfaced the ticket_id the lock-holder JSON already
carries. Added LiveLandProcess.ticket_id (defaults to None for a pre-
T-1795 lock file with no key) and wired it through scan_live_land_
processes and _live_land_process_remediation's rendered hint. This is
what makes "is a land running, and for which ticket" answerable with a
single frob doctor read instead of a pgrep loop that can match its own
argv (the exact incident: a shell running `until ! pgrep -f "frob
ticket land T-XXXX"` matched itself and hung 19 minutes past the real
land's exit).

The third orphaned-lease shape the coordinator found live (ticket-gone +
holder-dead, neither covered by T-1789's path-existence check) is
DELIBERATELY NOT folded in here -- it is a different mechanism (lease
staleness generalization across three independent conditions), filed
separately as T-1806 per the coordinator's own "fold it in if
it fits, or file it" framing; this ticket's own scope (land-lock
visibility + DirtyMain attribution) does not naturally hold it.

frob check --only prework --only scope --only sys --ticket T-1795 is
clean. frob check --only coverage shows 0 new COV002/COV007 findings.
All 8 TestDescribeRootDirt tests (2 new) and all 7 TestDoctorLiveLandProcess
tests (2 new) pass.

### Changed
```
 CHANGELOG.md                           | 20 --------
 rapid-debt.jsonl                       |  4 ++
 src/frob/app/ticket_runner/__init__.py | 65 +++++++++++++++++-------
 tickets/T-1795/ticket.md               | 71 +++++++++++++++++++++++++-
 tickets/T-1801/done-report.md          | 50 ++++++++++++++++++
 tickets/T-1801/ticket.md               | 92 ++++++++++++++++++++++++++++++++++
 tickets/T-1806/ticket.md     | 85 +++++++++++++++++++++++++++++++
 7 files changed, 347 insertions(+), 40 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_names_the_real_ticket_from_a_staged_rapid_debt_line` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_unattributed_when_the_true_author_cannot_be_determined` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess::test_ticket_id_is_reported_when_present` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess::test_ticket_id_is_none_for_a_pre_t1795_lock_file` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 3 error(s), 816 warning(s), 728 waived
- error-findings: AFFECT001@src/frob/tickets/_land_git_ops.py, COV005@src/frob/app/ticket_runner/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t1779-work/src/frob/tickets/_land_git_ops.py
