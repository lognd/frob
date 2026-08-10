---
id: T-2030
title: A detached background sweep (T-1983-shaped) writes uncommitted ticket-file
  content directly into an unrelated agent's worktree
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED 2026-08-10, in worktree .claude/worktrees/t1969-series while
working T-1964. `git status` unexpectedly showed unstaged modifications
to FIVE ticket files I had never touched and hold no lease on:
tickets/T-1988/ticket.md, tickets/T-1998/ticket.md,
tickets/T-1998/done-report.md, tickets/T-2000/ticket.md,
tickets/T-2008/ticket.md, tickets/T-2022/ticket.md.

`git diff HEAD` on these files showed real content divergence from my
own branch's last commit, not a line-ending artifact -- e.g.
tickets/T-1998/ticket.md's on-disk copy had its entire "## Done report"
section (57 lines, including another agent's evidence/attribution
writeup) silently stripped relative to my own HEAD; tickets/T-2008/
ticket.md (a ticket I dropped myself, with my own drop reason already
committed) had a DIFFERENT "auto-dropped by T-1983" drop-reason block
appended on disk, duplicated twice, that I never wrote and never
committed.

This is best explained by a detached background process -- the T-1983
auto-drop sweep mechanism (see T-2006, "T-1983's auto-drop only runs
inside the next sweep") or a similarly-shaped rapid post-land sweep --
writing ticket files directly to a path that is NOT scoped to the
worktree that spawned it, so its writes land on disk in an unrelated
agent's worktree rather than the worktree/root it actually belongs to.
Nothing was committed by either side at the time I observed it, so no
git history was corrupted -- but had I not run `git status`/`git diff
HEAD` before committing (I was about to, for an unrelated ticket-scope
gate check), my next ledger-touching frob verb would have auto-committed
this stray content into an unrelated ticket's land, exactly the T-1403
"ledger auto-commits sweep the whole index" failure mode the playbook
already documents for git-stash mishaps -- except here the corrupting
write comes from ANOTHER agent's/process's background sweep, not from
my own mistake, so no amount of personal discipline (never stash, never
touch unrelated files) prevents it.

Recovery: `git checkout HEAD -- <the 6 files>` restored my worktree to
its own last-committed state, confirmed byte-identical to current main's
committed content for those paths (content-diff clean; only CRLF/LF
`diff` noise remained). Did not investigate the writer process further
-- that requires reading the T-1983/rapid-sweep dispatch code path,
which is out of my own ticket's declared scope
(docs/modules/gates.md only).

Filed as a bug rather than fixed here: whatever spawns the T-1983-style
detached sweep needs to resolve its OWN write target from something
that cannot alias a concurrent agent's unrelated worktree path (a lease-
scoped root, not a bare cwd-relative or ambient resolution) -- same
class of root-resolution bug this repo has already hit once
(`frob ticket land`'s own T-1003 fix for `--worktree` root resolution,
referenced in this same session's T-1969 land output). Needs
investigation into exactly which detached-sweep code path performed
these writes and why its target resolved into a worktree that never
requested it.
