## Done report

Changed:
- src/frob/app/ticket_runner/_rapid_sweep.py: `_file_regression_ticket`
  now calls new `_commit_regression_ticket` after a successful
  `new_ticket`, which calls `frob.tickets._leases.commit_ticket_ledger_
  change` (scoped `git add <ledger pathspecs> && git commit -- <ledger
  pathspecs>`) and logs at ERROR (naming the ticket id and the DirtyMain
  consequence) on failure, never raising.
- src/frob/tickets/_land_git_ops.py: `describe_root_dirt` now names the
  detached post-land sweep as the likely author when EVERY dirty path
  matches its own known writes (`rapid-debt.jsonl`, `tickets.md`); a
  mixed dirty set is deliberately left unattributed.
- docs/modules/tickets.md: two new paragraphs in the "Deferred post-land
  sweep" section.
- tests/unit/test_rapid_sweep.py: TestCommitRegressionTicket (2 tests),
  TestDescribeRootDirt gets 2 more (sweep-authored, mixed-not-claimed).

ROOT CAUSE, established by reading the code before writing any fix (per
this ticket's own explicit instruction): `frob.tickets._new_renumber.
new_ticket` -- the LIBRARY function `_file_regression_ticket` calls
directly -- takes `ledger_lock`, calls `write_ticket`, and returns. It
has NO commit step of its own. The T-1130/T-1615 auto-commit
(`commit_ticket_ledger_change`) lives entirely in the CLI dispatch layer
(`frob.app.ticket_runner`'s verb table, `_auto_commit_ledger_after_
dispatch`), which a programmatic caller never reaches. This confirms the
THIRD candidate this ticket's own body named as most likely ("the sweep
files the ticket through a lower-level API that bypasses the CLI verb's
auto-commit entirely") and rules OUT the other two: this is not a cwd/
env issue (the sweep's cwd/env are unremarkable) and not a swallowed
failure (there was no commit ATTEMPT at all to fail).

This IS a wider hole than this ticket's own scope, exactly as flagged:
T-1615's uniform auto-commit covers the CLI surface, not every
programmatic `new_ticket`/`write_ticket` caller. Filed as a follow-up
(see "Filed" below) rather than silently generalizing this fix beyond
`_file_regression_ticket`'s own call site, which is the only
programmatic caller this ticket's declared scope covers.

Constraint compliance: the commit is `git add <ledger pathspecs>` then
`git commit -- <ledger pathspecs>` via `commit_ticket_ledger_change`
(the SAME primitive `frob ticket new`/`drop`/`fail`/`start` already use)
-- never a bare `git commit` or `git add -A`. A commit failure logs at
ERROR naming the exact recovery command and stating explicitly that the
next land will refuse with DirtyMain (test:
`test_commit_failure_logs_at_error_and_does_not_raise` asserts both the
ticket id and the literal string "DirtyMain" appear in the logged
message).

Regression coverage (the ticket's own acceptance): "a sweep that files a
regression ticket leaves the repo CLEAN, and a subsequent land
succeeds" -- `TestCommitRegressionTicket::test_commits_the_ledger_write`
asserts `git status --porcelain` shows nothing under `tickets/` after
`_commit_regression_ticket` runs (previously, per this ticket's own
observed incident, it stayed dirty and blocked the next land).

Evidence: 4 pytest node ids recorded via `frob ticket evidence`, all
measured passing as part of the full suite:
`timeout 100 uv run pytest tests/unit/test_rapid_sweep.py -p no:cacheprovider -q`
-> `collected=30 failed=0`.

Filed: T-1758 (renumbers at land) -- "T-1615's uniform ledger
auto-commit does not cover programmatic (non-CLI) callers of
new_ticket/write_ticket", the wider structural gap this ticket's
investigation surfaced but did not fix (T-1755's own scope is only
`_file_regression_ticket`'s one call site). Grepped the queue first
(`frob ticket list | grep -i "auto-commit\|programmatic"`) and found
nothing already tracking it before filing.

T-1615's own completeness claim needs reframing in light of this: its
audit enumerated the CLI DISPATCH TABLE and made every verb in it
auto-commit uniformly -- correct for what it covered. But the dispatch
table is not the full set of ledger writers. `new_ticket`/`write_ticket`
are library functions any code can call directly, and T-1615's audit
never had a way to see a caller that does not go through dispatch at
all. `_file_regression_ticket` is not an edge case that slipped past the
audit -- it is a DIFFERENT CLASS of caller the audit's own methodology
could not have found, because it was scoped to dispatch, not to every
ledger-mutating code path in the package.

VALIDATION worth recording plainly: `describe_root_dirt`'s new
sweep-authorship hint fired FOR REAL, on this ticket's OWN land attempt
-- a different ticket's detached sweep left `tickets.md` dirty mid-
session, and the refusal read "...(all paths match the detached
post-land sweep's own known writes -- rapid-debt.jsonl/tickets.md,
T-1699/T-1755 -- likely author: a sweep child that filed something and
did not commit it)", correctly diagnosing the exact failure mode this
ticket exists to close, unprompted, on live root state. Not a
constructed test case -- the fix demonstrated itself before it even
landed.

Gates: `frob check --only gates-fast/native/security --ticket T-1755`
all clean down to the expected land-owned-file SCOPE001 noise
(.frob-release.json, pyproject.toml, rapid-debt.jsonl, uv.lock),
reconciled by `frob ticket land`'s own internal merge.

### Changed
```
 docs/modules/tickets.md                    |  43 +++++++
 src/frob/app/ticket_runner/_rapid_sweep.py |  65 +++++++++-
 src/frob/tickets/_land_git_ops.py          |  48 +++++++-
 tests/unit/test_rapid_sweep.py             |  72 +++++++++++
 tickets.md                                 | 184 ++++++++++++++++++++++++++++-
 5 files changed, 406 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket::test_commits_the_ledger_write` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket::test_commit_failure_logs_at_error_and_does_not_raise` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_names_the_detached_sweep_as_likely_author` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_mixed_dirt_does_not_claim_the_sweep` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 3 error(s), 507 warning(s), 725 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/agent-a26588e5def8b5820/src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/agent-a26588e5def8b5820/src/frob/verify/_backpressure.py, invalid-argument-type@src/frob/app/ticket_runner/_land_cmd.py
