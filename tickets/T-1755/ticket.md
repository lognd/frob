---
id: T-1755
title: The detached post-land sweep leaves its filed regression ticket uncommitted,
  blocking every subsequent land
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/tickets/_new_renumber.py
- tests/unit/test_rapid_sweep.py
- docs/modules/tickets.md
- src/frob/tickets/_land_git_ops.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: requirement 3 names the likely author (the detached post-land sweep) when
    the dirty path is one it owns (tickets.md/rapid-debt.jsonl) -- describe_root_dirt
    lives here
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: requirement 3 names the likely author (the detached post-land sweep) when
    the dirty path is one it owns (tickets.md/rapid-debt.jsonl) -- describe_root_dirt
    lives here
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket::test_commits_the_ledger_write
- tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket::test_commit_failure_logs_at_error_and_does_not_raise
- tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_names_the_detached_sweep_as_likely_author
- tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_mixed_dirt_does_not_claim_the_sweep
designated_repro_test: null
threat: null
component: null
---
The detached post-land sweep writes to the SHARED ROOT LEDGER and does
not commit what it writes. The uncommitted write then refuses every
subsequent land repo-wide with `DirtyMain`, and no agent can clear it --
they are correctly isolated from root.

Observed 2026-08-07. After a land, the sweep found 2 new errors,
auto-filed them via `frob ticket new` (correct -- that is the whole
design), and left `tickets.md` dirty. The next agent's land refused three
times across several minutes with 30s waits. It correctly concluded the
state was not transient, and correctly reported instead of forcing.
Nothing was going to clear it: the only process that could commit was the
coordinator, by hand.

This is the SECOND uncommitted write from the same detached child. T-1699
already covers the `rapid-debt.jsonl` line racing the DirtyMain check
outside the land lock. This is a distinct instance -- the regression
TICKET is a separate write to a separate tracked file -- and the pair
together says the general rule was never applied: ANY tracked-file write
the detached sweep makes must be committed by the sweep, or it becomes a
repo-wide land block.

Note `frob ticket new` DOES auto-commit (T-1130), and `frob ticket
archive`/every other ledger verb now does too (T-1615). So the write
should have committed itself. Establish why it did not before fixing
anything -- plausible causes worth checking in order:

- the sweep runs with a cwd or env where the auto-commit path is skipped;
- the auto-commit ran and FAILED (index contention with a concurrent
  land is the obvious candidate) and the failure was swallowed;
- the sweep files the ticket through a lower-level API that bypasses the
  CLI verb's auto-commit entirely.

The third is the most likely and the most important to rule in or out,
because it would mean T-1615's uniform auto-commit covers the CLI surface
but not programmatic callers -- which is a much wider hole than this
ticket.

REQUIRED:

1. The detached sweep commits EVERY tracked-file write it makes --
   `rapid-debt.jsonl` (T-1699) and any filed regression ticket -- scoped
   to those paths only, never a bare `git commit` or `git add -A`. A
   blanket add on a root checkout that concurrent lands are racing
   against is how 1416 lines of another agent's in-flight work got
   published under an unrelated commit message earlier today (T-1740).
2. If the commit fails, LOG AT ERROR naming the file and the fact that
   the next land will refuse. A silent failure here converts a background
   nicety into a fleet-wide stall with no visible cause -- which is
   exactly what happened.
3. `DirtyMain`'s message should name the likely author when the dirty
   path is one the sweep owns (`tickets.md`, `rapid-debt.jsonl`), because
   the agent seeing that error is structurally unable to investigate it.
   T-1740 already made the message name staged state; this is the
   same principle extended to WHO.

Regression coverage: a sweep that files a regression ticket leaves the
repo CLEAN, and a subsequent land succeeds. Assert the actual invariant
-- root clean after the sweep completes -- not that a commit helper was
called.