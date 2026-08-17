---
id: T-1891
title: frob ticket new prints a DirtyMain --no-commit warning even when it DID commit
  the ledger
state: done
kind: bug
origin: agent
created: '2026-08-09'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_leases.py
- src/frob/tickets/_new_renumber.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_leases.py
  reason: the no-commit-warning condition and its two internal batching callers
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/tickets/_new_renumber.py
  reason: the no-commit-warning condition and its two internal batching callers
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: the no-commit-warning condition and its two internal batching callers
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: the no-commit-warning condition and its two internal batching callers
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_ticket_leases.py
  reason: the no-commit-warning condition and its two internal batching callers
  actor: logan
  at: '2026-08-09'
evidence:
- tests/test_ticket_leases.py::TestNewDropFailAutoCommit::test_new_without_no_commit_never_warns_dirty
- tests/test_ticket_leases.py::TestNewDropFailAutoCommit::test_new_with_no_commit_still_warns_dirty
- tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_no_commit_flag_with_warn_if_dirty_false_stays_silent
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_no_attribution_files_everything_as_before
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-09, coordinator, on main. Ran 'frob ticket new ...' with no --no-commit flag. It printed:

  WARNING: tickets: T-1890 ledger change left DIRTY by --no-commit -- this WILL DirtyMain-block every concurrent 'frob ticket land' ... Fix: git add tickets/T-1890 tickets.md && git commit ...

but it had ALREADY committed the change itself (commit 9ca6bba96, tree clean immediately after). The recommended remediation then failed with 'nothing to commit, working tree clean'.

WHY IT MATTERS. DirtyMain deadlock is one of this repo's most expensive known footguns, so this warning is one an operator is trained to act on instantly. Crying wolf on the clean path is worse than silence: it teaches coordinators to ignore the one message that actually matters, and it burns a redundant commit round-trip during a live multi-agent wave.

FIX. Gate the warning on the ACTUAL post-write worktree state (or on the --no-commit flag genuinely being set), not on an unconditional code path. Add a regression test asserting the warning is absent when 'ticket new' commits, and present when --no-commit is passed.

## Done report

Root cause confirmed by direct investigation, reproducing the coordinator's live 2026-08-09
incident exactly: `frob.tickets._new_renumber.new_ticket` (T-1758) auto-commits its own ledger
write via `commit_ticket_ledger_change`, and `frob.app.ticket_runner._new._new` calls it with
`no_commit=True` -- NOT because the user passed `--no-commit`, but purely as an internal
batching device so `_new`'s OWN outer `commit_ticket_ledger_change` call a few lines later
(bound to the REAL `cfg.ticket_no_commit` flag) captures the whole filed block -- title, scope,
body, and any `--evidence` ids -- in one commit instead of two. `commit_ticket_ledger_change`'s
`no_commit=True` branch warns "left DIRTY by --no-commit" whenever the ledger is dirty at that
call -- which is ALWAYS true for the internal batching call, by construction, since the point of
batching is writing before the real commit. The warning was therefore never reading the actual
--no-commit flag's outcome: it fired on every single `frob ticket new`, no matter what, and was
simply papered over by the fact that the outer call usually committed a split second later. The
same shape existed in `frob.app.ticket_runner._rapid_sweep._file_regression_ticket`, which calls
`new_ticket(..., no_commit=True)` for the identical batching reason ahead of its own
`_commit_regression_ticket` retry loop.

Fix: added a `warn_if_dirty: bool = True` parameter to `commit_ticket_ledger_change`
(src/frob/tickets/_leases.py) that gates ONLY the warning, never the commit-skip itself, and
threaded it through `new_ticket`/`_commit_new_ticket` (src/frob/tickets/_new_renumber.py). The
two internal batching call sites (`_new._new`, `_rapid_sweep._file_regression_ticket`) now pass
`warn_if_dirty=False` explicitly, since each is immediately followed, unconditionally, by its own
real commit attempt for the same pathspecs. A caller that invokes `new_ticket` directly as a
library function with a genuine `no_commit=True` (never issues its own separate commit afterward) still gets the
default `warn_if_dirty=True` and is still warned correctly -- verified this stays true via the
pre-existing `TestNewTicketProgrammaticAutoCommit.test_no_commit_leaves_ledger_dirty_and_warns`
regression, which failed when a first (over-broad) attempt at this fix blindly suppressed the
warning for every `no_commit=True` call regardless of caller. `commit_ticket_ledger_change`'s
own docstring gained a T-1891 section spelling out the exact contract a `warn_if_dirty=False`
caller must uphold (a real unconditional follow-up commit for the same pathspecs).

Both directions verified: plain `frob ticket new` (no `--no-commit` anywhere) no longer prints
'left DIRTY by --no-commit' and the ledger really is committed afterward; a genuine `frob ticket
new --no-commit` still prints the warning and really does leave the ledger dirty. Verified failing
at the parent commit (the plain-`new` case DID print the spurious warning) and passing after the
fix, for all three new tests plus the untouched pre-existing programmatic-caller warning test.

### Changed
```
 tickets/T-1891/done-report.md | 54 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-1891/ticket.md      | 39 ++++++++++++++++++++++++++++++-
 2 files changed, 92 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestNewDropFailAutoCommit::test_new_without_no_commit_never_warns_dirty` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestNewDropFailAutoCommit::test_new_with_no_commit_still_warns_dirty` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_no_commit_flag_with_warn_if_dirty_false_stays_silent` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_no_attribution_files_everything_as_before` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 3 error(s), 972 warning(s), 700 waived
- error-findings: AFFECT001@src/frob/app/ticket_runner/_rapid_sweep.py, PRE001@tickets/T-1891, REG002@docs/design/registry/check-coverage.yaml
