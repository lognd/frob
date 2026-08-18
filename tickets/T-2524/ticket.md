---
id: T-2524
title: agent scratch files in the repo root get committed by the next land
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/guides/agent-playbook.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Five files -- done-report-t1135.md, -t1137.md, -t1219.md, -t2468.md,
-t2478.md -- were TRACKED IN GIT in the repo root. Removed 2026-08-18
after verifying every non-blank line of each was already present verbatim
in the corresponding canonical tickets/<id>/done-report.md, so nothing
was lost.

MECHANISM: an agent writes its done-report prose to a scratch file so it
can pass --body-file (the shell-quoting-safe route, which the tooling
itself recommends over --body for text containing backticks). `frob
ticket done-report` splices that text into the canonical location. The
INPUT file is never cleaned up, and because it sits in the repo root, the
next land's "commit everything" step commits it.

A .gitignore rule for `done-report-*.md` has landed as an immediate stop,
but that is a STOPGAP AND IT HAS A COST WORTH STATING: a gitignored file
does not appear in `git status --porcelain`, so T-2487's root-cleanliness
detector and the DirtyMain guards can no longer see it either. We have
traded "stray file gets committed" for "stray file is invisible". That is
the better trade today, and it is not the right end state.

WHAT THE REAL FIX LOOKS LIKE (pick one, do not do all three):
1. Give agents a sanctioned scratch location outside the repo (or under a
   path the land provably never stages) and say so in the playbook, so
   the shape stops being produced at all. This is the preferred fix --
   it removes the failure rather than hiding it.
2. Have `frob ticket done-report --body-file` consume-and-delete its
   input when the input lives inside the repo, so the file cannot outlive
   the command that read it.
3. Make the land REFUSE to stage repo-root files matching a scratch
   shape, naming them, rather than silently sweeping them in.

Note that the land committing an unrelated root file is the general
defect here; done-reports are just the instance we caught. Anything an
agent leaves in the root gets committed by the next land, which is also
how this repo's DirtyMain deadlocks start.

POSITIVE CONTROL: after the fix, an agent following the normal
--body-file flow must leave the repo root clean with no gitignore rule
required to achieve it; verify by running the flow and checking
`git status --porcelain` AND `git ls-files` (the second matters -- the
gitignore stopgap makes the first pass vacuously).

ALSO NOTED WHILE INVESTIGATING, separate concern, file separately if
worth acting on: `git gc` is failing on this repo ("too many unreachable
loose objects; run 'git prune'", .git/gc.log present, automatic cleanup
disabled until the log is removed). Likely accumulated from ~30 agent
worktrees and repeated land squashes. Not urgent, but it means git
housekeeping has been silently off for some time.
