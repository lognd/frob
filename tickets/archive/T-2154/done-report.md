## Done report

CORRECTED FINAL OUTCOME (supersedes both earlier Done reports on this
ticket): T-2154's original E402 finding (tests/test_ticket_leases.py,
pytestmark landing above an existing import) was independently fixed by
T-2099's own land before this ticket's first land attempt. Confirmed with
`git merge main` into this worktree followed by `git diff main --
tests/test_ticket_leases.py`, which is EMPTY -- the file at main's tip
already matches this worktree's copy exactly, byte for byte.

Two earlier attempts to "fix" this ticket in this worktree are reverted:
- b34392eb1 re-fixed the already-fixed E402 (redundant, harmless, but a
  fix for a problem main no longer had).
- 87a3e3f6d wrapped three lines that read as E501 (96 > 88) ONLY when
  linted at a path outside tests/ or with `ruff --isolated` (which
  discards pyproject.toml's [tool.ruff.lint.per-file-ignores]
  "tests/**" = ["E501"] entirely). At the file's real path with the
  repo's own config, `ruff check --select E402,E501` reads clean --
  confirmed directly, no such finding exists. This commit is reverted
  (cfff74962) as unnecessary churn based on a measurement artifact, not a
  real finding. No E501-in-tests bug exists; nothing filed for it.

The genuine remaining quarantine cause today (E501:
src/frob/verify/_quarantine.py, introduced by T-2132's land, under src/
so genuinely NOT exempted) is out of this ticket's scope and is being
handled by that ticket's own line.

Closing this ticket as already-satisfied by T-2099's land. No code change
of this ticket's own survives in the final worktree state (net diff
against main for tests/test_ticket_leases.py is empty).

frob:waive BUG002 reason="this ticket's defect (an E402 in tests/test_ticket_leases.py) was independently fixed by T-2099's own land before this ticket's first close attempt -- there is no fix of THIS ticket's own to reproduce as fail-at-parent/pass-at-fix, since the parent commit already carries T-2099's fix (git diff main -- tests/test_ticket_leases.py is empty in this worktree); the designated evidence test necessarily passes at parent because the defect was already gone by the time this ticket reached its parent commit, not because the evidence is weak"

### Changed
```
 tickets/T-2154/done-report.md | 45 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2154/ticket.md      | 17 ++++++++++++++--
 2 files changed, 60 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/t-2154/src/frob/verify/_quarantine.py, SELFAUDIT001@design, TICK004@tickets.md
