---
id: T-2154
title: 'post-land sweep regression from T-2125: 2 new (rule, file) identit(ies), 5
  finding(s) (E402, E501)'
state: done
kind: bug
origin: agent
created: '2026-08-11'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- /home/logan/projects/frob/tests/test_ticket_leases.py
evidence_scope:
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: /home/logan/projects/frob/src/frob/tickets/_unlanded.py
  reason: 'T-2156''s dispatch instructed touching only tests/test_ticket_leases.py''s
    E402; the E501 in src/frob/tickets/_unlanded.py is owned by T-1966''s holder.
    Narrowing T-2154''s scope to avoid a lease conflict with that agent.

    '
  actor: logan
  at: '2026-08-11'
evidence:
- tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-2125 at commit 5da87ec3f37553aac0c9b552e64efdcfa2805650 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 5 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- E402  /home/logan/projects/frob/tests/test_ticket_leases.py
- E501  /home/logan/projects/frob/src/frob/tickets/_unlanded.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- E402  /home/logan/projects/frob/tests/test_ticket_leases.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/src/frob/tickets/_unlanded.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

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
