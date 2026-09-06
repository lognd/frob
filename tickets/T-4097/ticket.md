---
id: T-4097
title: 'F-297: ticket verbs do not walk up to the ledger root, so running from a subdirectory
  reports ''No ticket with that id'''
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/__init__.py
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
Consumer logand.app-v2 F-297, 2026-09-06:

  "`frob ticket evidence` run from frontend/ fails with 'NotFound: No ticket with
   that id'; ONLY THE WORKTREE ROOT WORKS. The verb should WALK UP TO THE LEDGER
   ROOT LIKE GIT DOES."

ROOT RESOLUTION DOES NOT WALK UP. Running a ticket verb from any subdirectory of a
real frob repo resolves that subdirectory as the root, finds no tickets/ there,
and reports the ticket as NOT FOUND. Every other tool a developer uses in a repo
-- git first among them -- walks up to the repo root, so the expectation is
universal and the failure is surprising.

THE ERROR IS THE WORST PART: "No ticket with that id" is a claim about the
TICKET, when the actual problem is the RESOLVED ROOT. It sends the user to check
the id, the ledger, and their own typing -- everywhere except the one thing that
is wrong. A user who trusts that message concludes their ticket is missing.

THIS PAIRS WITH T-4085, WHICH JUST LANDED, AND THE PAIR IS INSTRUCTIVE. That
ticket made `frob ticket new` REFUSE when the resolved root has neither frob.toml
nor .git -- the fix for a consumer who wrote sixty tickets into a /tmp scratchpad.
Both defects share one cause: ROOT RESOLUTION FALLS BACK TO BARE cwd WITH NO
NOTION OF A CONTAINING REPO. T-4085 addressed the case where cwd is OUTSIDE any
repo; this is the case where cwd is INSIDE one but below its root.

NOTE T-4085 ALREADY IMPROVES THIS CASE, INCIDENTALLY: `frontend/` has no
frob.toml and no .git, so a verb run there now refuses with a message naming the
resolved directory rather than claiming the ticket does not exist. That is
strictly better -- but it is still a refusal where the right answer is to find the
ledger. VERIFY WHAT THE MESSAGE SAYS TODAY before designing; the consumer's report
predates that landing and the symptom may already have changed shape.

THE FIX: walk up from cwd looking for the ledger root (frob.toml, or .git), as
git does, and use the first one found. Then T-4085's refusal becomes what it
should be -- the case where NO containing repo exists at any level, which is the
genuinely unrecoverable one.

DETERMINE FIRST, because it interacts with two open tickets:
  - T-3983 records that ticket-store WRITES resolve from cwd, so a stale worktree
    captures them. WALKING UP MUST NOT MAKE THAT WORSE: from inside a worktree,
    walking up finds the worktree's own root, which is correct for reads and is
    exactly the ambiguity T-3983 is about for writes. Read it before implementing.
  - T-4085 deliberately left explicit --path/FROB_ROOT untouched as a deliberate
    pin. Walk-up must apply only to the ambient-cwd path, for the same reason.

MUST-FIRE FIXTURE: a ticket verb run from a subdirectory of a frob repo finds the
ledger and operates on the right ticket.
MUST-STAY-QUIET: (a) --path/FROB_ROOT still pins explicitly and is not overridden
by walk-up; (b) a directory with no containing repo at any level is still refused
per T-4085.
THIRD FIXTURE: from inside a worktree, walk-up resolves the WORKTREE's root, not
the primary's -- or does so deliberately per whatever T-3983 settles.

ACCEPTANCE
- Walk-up implemented for the ambient-cwd path only.
- The "No ticket with that id" message no longer stands in for a root-resolution
  failure.
- Read against T-3983 and T-4085, with the worktree case stated.
- All three fixtures committed.