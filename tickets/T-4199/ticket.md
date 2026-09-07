---
id: T-4199
title: abandoned git merge temporary files dirty the shared root and block fleet dispatch,
  and the obvious cleanup would delete a freshly filed ticket
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .gitignore
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given merge temporary files in the root, when dispatch readiness is checked,
    then they do not make the tree dirty
  evidence: []
- text: given an untracked ticket directory in the root, when dispatch readiness is
    checked, then the tree is still reported dirty
  evidence: []
- text: given the operation that creates merge temporary files, when it is interrupted,
    then it removes them on its error path
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A MERGE LEFT THREE TEMPORARY FILES IN THE PRIMARY CHECKOUT AND NOTHING CLEANED
THEM UP, DIRTYING THE SHARED ROOT AND BLOCKING DISPATCH. Found while checking
whether it was safe to dispatch an agent.

MEASURED, 2026-09-07:

    ?? .merge_file_JKtYny
    ?? .merge_file_XVqlm0
    ?? .merge_file_fhutG6

    no MERGE_HEAD, no MERGE_MSG -- no merge in progress
    no live merge or land process
    files roughly nine minutes old
    the pattern is NOT in this repository's ignore file

So they are abandoned residue from a merge that completed or was killed. Git
writes these while running its three-way merge machinery and normally removes
them; a merge that is interrupted, or one whose driver exits abnormally, leaves
them behind.

WHY THIS IS WORSE THAN LITTER. A dirty shared root DirtyMain-blocks every
concurrent agent land, and this repository's own fleet status refuses to
recommend dispatch while the root is dirty. So three abandoned temporary files
stall the whole fleet, and the cause is invisible: the files have machine-
generated names, appear in no ticket's scope, and nothing in any agent's output
mentions them. I only found them because I check root cleanliness before
dispatching.

THE CLEANUP IS ALSO A TRAP, WHICH IS THE PART WORTH ENCODING. The obvious
remedy -- a blanket clean of untracked files -- WOULD HAVE DESTROYED WORK. At the
moment I found these, the root also held an untracked ticket directory belonging
to a planner mid-filing-burst. A blanket clean would have deleted a freshly filed
ticket that no commit yet referenced. I removed the three files BY NAME for
exactly that reason, and any automated cleanup must do the same.

WHAT TO DO
  1. Add the merge temporary pattern to the ignore file. Cheapest fix, removes the
     dispatch-blocking property entirely, and costs nothing -- these files are
     never wanted in a commit.
  2. Find out which operation leaves them. The three appeared within four seconds
     of each other while ledger mirroring and a land were both active. If our own
     merge driver or the ledger mirror is invoking git's merge machinery and not
     cleaning up on an error path, that is the real defect and the ignore entry
     only hides it.
  3. Do NOT add a blanket untracked-file clean anywhere. This repository has an
     open finding about a killed verb leaving a half-filed ticket directory
     behind; a cleanup that removes untracked files indiscriminately would turn
     that into data loss. Clean by name or by an explicit pattern, never by
     category.

MUST-FIRE FIXTURE:   a merge temporary file present in the root does not make the
                     tree dirty for dispatch purposes.
MUST-STAY-QUIET:     an untracked ticket directory still makes the tree dirty --
                     that signal is real and must not be suppressed alongside.
THIRD FIXTURE:       whatever operation creates these removes them on its error
                     path, proven by interrupting it.

ACCEPTANCE
- The merge temporary pattern ignored.
- The creating operation identified and its cleanup fixed, or the reason it
  cannot be recorded.
- No blanket untracked-file cleanup introduced.
- All three fixtures committed.
