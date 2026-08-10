---
id: T-1795
title: Advisory-visible land lock (retire pgrep polling; fix DirtyMain misattribution)
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_leases.py
- src/frob/doctor.py
- src/frob/tickets/_land_git_ops.py
- tests/unit/test_rapid_sweep.py
- tests/system/test_cli_doctor.py
- src/frob/app/ticket_runner/__init__.py
- tickets/T-1795/ticket.md
- tickets/T-1801/done-report.md
- tickets/T-1801/ticket.md
- tickets/T-1806/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: describe_root_dirt/_likely_sweep_authored (the DirtyMain misattribution
    fix) live in _land_git_ops.py, not _leases.py; their existing test coverage lives
    in test_rapid_sweep.py
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: describe_root_dirt/_likely_sweep_authored (the DirtyMain misattribution
    fix) live in _land_git_ops.py, not _leases.py; their existing test coverage lives
    in test_rapid_sweep.py
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/system/test_cli_doctor.py
  reason: TestDoctorLiveLandProcess in this file holds scan_live_land_processes/LiveLandProcess's
    own test coverage; the new ticket_id field needs a test there
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/ticket_runner/__init__.py
  reason: carried on this same branch from T-1801's own land and this worktree's earlier
    ticket-management ops (not touched by T-1795's own code); tickets/T-1795/ticket.md
    is this ticket's own v2 ledger file
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1795/ticket.md
  reason: carried on this same branch from T-1801's own land and this worktree's earlier
    ticket-management ops (not touched by T-1795's own code); tickets/T-1795/ticket.md
    is this ticket's own v2 ledger file
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1801/done-report.md
  reason: carried on this same branch from T-1801's own land and this worktree's earlier
    ticket-management ops (not touched by T-1795's own code); tickets/T-1795/ticket.md
    is this ticket's own v2 ledger file
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1801/ticket.md
  reason: carried on this same branch from T-1801's own land and this worktree's earlier
    ticket-management ops (not touched by T-1795's own code); tickets/T-1795/ticket.md
    is this ticket's own v2 ledger file
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1806/ticket.md
  reason: carried on this same branch from T-1801's own land and this worktree's earlier
    ticket-management ops (not touched by T-1795's own code); tickets/T-1795/ticket.md
    is this ticket's own v2 ledger file
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_names_the_real_ticket_from_a_staged_rapid_debt_line
- tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_unattributed_when_the_true_author_cannot_be_determined
- tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess::test_ticket_id_is_reported_when_present
- tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess::test_ticket_id_is_none_for_a_pre_t1795_lock_file
designated_repro_test: null
threat: null
component: null
---
Merges T-draft-736f2d46's original ask (requirement 4 from T-1779: an
advisory-visible land lock, not discoverable only by `pgrep`) with two
concrete pieces of live evidence that make it a confirmed bug, not a
nice-to-have.

REQUIREMENT (unchanged from T-draft-736f2d46): a `frob doctor`-style
line, or a marker file, that names which ticket is landing and whether
the lock is CURRENTLY held -- readable without `pgrep`, without any
side effects, and without racing the same self-matching hazard below.

EVIDENCE 1 -- DirtyMain misattributes the owner of staged dirt. T-1222's
detached post-land sweep child failed to commit its own write to
`rapid-debt.jsonl`, leaving it STAGED in root. `describe_root_dirt`'s
T-1740 callout named T-1699/T-1755 as the likely author -- it GUESSED
from the file's usual owner (`_SWEEP_OWNED_DIRTY_PATHS`'s membership
test), not from who actually staged it. Three separate agents hit this
DirtyMain refusal, all three read the wrong ticket id in the message,
and none could diagnose the real cause from the refusal alone. Fix:
attribution must be SYMBOLIC (which process/commit staged this content
-- `git log`/reflog on the staged blob, or a marker the sweep child
itself writes naming its own ticket id before staging) and must say
"unattributed" when it cannot be determined, never a plausible-but-wrong
ticket id. Same "cannot verify is never verified" rule the sweep already
claims to follow elsewhere (T-1779's own docs section quotes this
exact rule for `_probe_worktree_liveness`'s ambiguous case) -- this is
the same rule applied to a message body, not just a return value.

EVIDENCE 2 -- `pgrep -f "frob ticket land"` (or any `until ! pgrep -f
"frob ticket land T-XXXX"` polling loop) is not a reliable land
detector and can hang forever on itself. A shell running exactly that
loop (`until ! ps aux | grep "ticket land" | grep -v grep`) matched its
OWN command line -- the loop's own argv contains the literal string
"ticket land T-XXXX" -- so the poller never saw an empty result even
after the real land process had long since exited. Found live: a shell
stuck 19 minutes in this exact loop, killed by the coordinator. This
polling recipe was recommended THIS SESSION (the playbook's own worked
example, `ps aux | grep "ticket land" | grep -v grep`) -- it needs
either a fix (a `grep -v` for the poller's own pid/pattern, fragile) or,
better, retirement in favor of reading the SAME advisory surface this
ticket is asking for (a lock file/doctor line a coordinator can read
once, no polling loop needed at all -- the self-matching hazard cannot
exist for a single stat/read).

Both pieces of evidence point at the same fix: make the land lock's
state a first-class, directly-readable fact (file existence + holder
metadata, or a `frob doctor` line), so neither "who staged this" nor
"is a land still running" ever again depends on grep pattern-matching a
process table that can match the watcher itself.

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
