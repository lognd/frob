---
id: T-1758
title: T-1615's uniform ledger auto-commit does not cover programmatic (non-CLI) callers
  of new_ticket/write_ticket
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_leases.py
- src/frob/tickets/_store.py
- src/frob/app/ticket_runner/_new.py
- docs/modules/tickets.md
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_rapid_sweep.py
- tests/test_ticket_leases.py
- tickets/T-1758/ticket.md
- tickets/T-1758/done-report.md
- tickets/T-1799/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: new_ticket now auto-commits internally (T-1758's structural fix); the CLI
    verb must opt out via no_commit=True to preserve its documented single-commit-including-evidence
    behavior, otherwise --evidence would split into two commits
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/tickets.md
  reason: new_ticket's public-api signature/behavior doc entry needs updating for
    the new no_commit parameter and auto-commit behavior
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: new_ticket's own auto-commit makes _rapid_sweep.py's existing per-caller
    wrapper redundant/stale -- its new_ticket call must opt out via no_commit=True
    to preserve its documented nicer commit message, and the test encoding the old
    'new_ticket does not commit' premise needs updating to match
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: new_ticket's own auto-commit makes _rapid_sweep.py's existing per-caller
    wrapper redundant/stale -- its new_ticket call must opt out via no_commit=True
    to preserve its documented nicer commit message, and the test encoding the old
    'new_ticket does not commit' premise needs updating to match
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_ticket_leases.py
  reason: new tests for new_ticket's own auto-commit behavior; v2 per-ticket ledger
    files
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1758/ticket.md
  reason: new tests for new_ticket's own auto-commit behavior; v2 per-ticket ledger
    files
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1758/done-report.md
  reason: new tests for new_ticket's own auto-commit behavior; v2 per-ticket ledger
    files
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1799/ticket.md
  reason: the misattribution follow-up draft filed as part of this ticket's own audit
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_ticket_leases.py::TestNewTicketProgrammaticAutoCommit::test_programmatic_call_auto_commits
- tests/test_ticket_leases.py::TestNewTicketProgrammaticAutoCommit::test_no_commit_leaves_ledger_dirty_and_warns
- tests/test_ticket_leases.py::TestNewTicketProgrammaticAutoCommit::test_new_verb_still_produces_one_commit_including_evidence
- tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket::test_commits_the_ledger_write
designated_repro_test: null
threat: null
component: null
---
T-1755's investigation confirmed: `frob.tickets._new_renumber.new_ticket`
(and, by the same construction, `write_ticket`/other `frob.tickets`
mutators called directly rather than through the `frob ticket <verb>` CLI
dispatch) has NO auto-commit of its own. The T-1130/T-1615 auto-commit
(`commit_ticket_ledger_change`, `_auto_commit_ledger_after_dispatch`)
lives entirely in the CLI dispatch layer -- it wraps the verb, not the
library call the verb happens to invoke.

`frob.app.ticket_runner._rapid_sweep._file_regression_ticket` was one
concrete victim (fixed in T-1755): it calls `new_ticket` directly (a
detached child, not a CLI dispatch), so its write went uncommitted and
DirtyMain-blocked every subsequent land repo-wide.

This is a STRUCTURAL gap, not just that one call site: ANY current or
future programmatic caller of `frob.tickets.new_ticket`/`write_ticket`/
other ledger mutators that does not go through `frob.app.ticket_runner`'s
CLI dispatch table inherits the exact same silent-DirtyMain hazard.

Scope for whoever picks this up: audit `frob.tickets` for every
programmatic (non-CLI) caller of a ledger-mutating function
(`new_ticket`, `write_ticket`, `add_evidence`, etc. -- grep for direct
imports from `frob.app.ticket_runner`-external modules) and decide,
per T-1755's own two options:

1. Move the auto-commit INTO the library function itself (so it is
   impossible to call any ledger mutator without committing), or
2. Establish a documented convention that every non-CLI caller must
   call `commit_ticket_ledger_change` itself immediately after, and add
   a gate/lint that catches a caller which does not.

Option 1 closes the hole permanently; option 2 is weaker (relies on every
future caller remembering) but may be necessary if some programmatic
caller legitimately wants to batch several ledger writes into one commit
(same shape `commit_ticket_ledger_change(..., no_commit=True)` already
supports for the CLI layer).

## Done report

T-1615's uniform ledger auto-commit only ever covered the `frob ticket
new` CLI dispatch path (`_auto_commit_ledger_after_dispatch` wraps the
dispatch call site) -- `new_ticket`, the LIBRARY function, never
committed. Every programmatic caller that bypasses the CLI inherited the
same silent-DirtyMain hazard: three separate fleet stalls today (T-1222's
sweep child leaving `rapid-debt.jsonl` staged, and `tickets/T-1792/` left
untracked) traced back to exactly this shape -- a ledger writer that
never commits, blocking every concurrent `frob ticket land` repo-wide.

Audit (per the ticket's own instruction to check every programmatic
writer, not just the one T-1755 already patched): grepped every
ledger-mutating function (`new_ticket`, `write_ticket`, `write_all`,
`add_evidence`) for callers outside `frob.tickets`/
`frob.app.ticket_runner`. Only `new_ticket` has real cross-module
programmatic callers:
- `frob.app.ticket_runner._rapid_sweep._file_regression_ticket` (T-1755's
  own fix, a per-caller wrapper -- exactly the "weaker, relies on every
  future caller remembering" option the ticket named)
- `frob.tickets._mutation_sweep_queue._file_confirmatory_only_ticket`
- `frob.testing._stability` (flake auto-quarantine)
- `frob.app.sys_runner._apply` (`frob sys plan`)
- `frob.fleet` (cross-repo ticket routing)

None of the other four had ANY commit step at all before this fix --
confirming the gap was live beyond the one site T-1755 patched.

Fix: moved the guarantee to the WRITE BOUNDARY (`new_ticket` itself)
rather than adding a fifth per-caller wrapper, per the instruction to
consider whether the guarantee belongs there instead of at each call
site. `new_ticket` now calls `commit_ticket_ledger_change` (the same
primitive the CLI dispatch layer already funnels through) before
returning, so every caller -- CLI or programmatic, present or future --
gets a committed ledger with nothing to remember. `no_commit: bool =
False` is `new_ticket`'s own opt-out, identical semantics to
`commit_ticket_ledger_change`'s own (still WARNS loudly when it leaves
the ledger dirty on purpose, never silently), for a caller that wants to
fold further ledger writes into ONE commit of its own:
- `frob ticket new`'s CLI handler (`_new.py`) now passes
  `no_commit=True` so its own final `commit_ticket_ledger_change` call
  -- which runs AFTER `--evidence` is applied -- is still the only
  commit, preserving the documented "one commit including evidence"
  behavior. Verified with a new regression test
  (`test_new_verb_still_produces_one_commit_including_evidence`)
  asserting exactly one new commit, not two.
- `_rapid_sweep._file_regression_ticket` now passes `no_commit=True` too,
  so its own existing `_commit_regression_ticket` wrapper still lands
  its more informative commit message (naming both the regression ticket
  id and the land it regressed from) instead of being silently
  superseded by `new_ticket`'s own generic message.
- The other three callers (`_mutation_sweep_queue`, `testing/
  _stability`, `sys_runner`) needed no change at all -- they now
  auto-commit for the first time, closing a real, currently-live gap.

On the misattribution note from the DirtyMain incidents today: land's
`DirtyMain`/`OutOfScopeWaiveDeletion` messages guess the offending
ticket from the dirty file's USUAL owner (recent git history), not from
who actually staged the uncommitted change -- this fix does not change
that attribution logic (out of scope: it lives in `frob.tickets._land`/
`_land_git_ops.py`, not `_new_renumber.py`/`_leases.py`/`_store.py`).
Writer identity is NOT made available at the point of failure by this
fix -- filed as a separate follow-up, T-1799 (renumbers at
land), scoped to `_land.py`/`_land_git_ops.py`, rather than silently
left for the next agent to independently rediscover the misattribution.

Evidence: `commit_ticket_ledger_change`/`write_ticket` themselves are
UNCHANGED -- this fix calls the existing primitive from a new call site,
adds no new capability, and needed no gate waivers.

### Changed
```
 docs/modules/tickets.md                    |  12 ++-
 src/frob/app/ticket_runner/_new.py         |   6 +-
 src/frob/app/ticket_runner/_rapid_sweep.py |   7 +-
 src/frob/tickets/_new_renumber.py          |  54 ++++++++++++++
 tests/test_ticket_leases.py                | 113 +++++++++++++++++++++++++++++
 tests/unit/test_rapid_sweep.py             |  11 ++-
 tickets/T-1758/ticket.md                   |  62 +++++++++++++++-
 tickets/T-1799/ticket.md         |  58 +++++++++++++++
 8 files changed, 314 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestNewTicketProgrammaticAutoCommit::test_programmatic_call_auto_commits` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestNewTicketProgrammaticAutoCommit::test_no_commit_leaves_ledger_dirty_and_warns` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestNewTicketProgrammaticAutoCommit::test_new_verb_still_produces_one_commit_including_evidence` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket::test_commits_the_ledger_write` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 982 warning(s), 725 waived
- error-findings: none (measured, zero errors)
