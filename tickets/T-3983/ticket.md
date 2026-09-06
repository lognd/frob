---
id: T-3983
title: Ticket-store WRITES resolve from cwd, so a stale worktree silently captures
  them and leaves a phantom lease on main
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_store.py
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
Consumer apollo, 2026-09-06 (r10/r11 wave):

  "CROSS-ROOT CWD HAZARD: frob commands run with cwd inside a stale worktree
   resolve against THAT root (ticket new/start/renumber landed a whole design
   ticket in a landed worktree's store; a phantom lease on main blocked new
   tickets until the worktree was deleted). frob ticket verbs could refuse to
   run from a worktree whose ticket is done, or always resolve the PRIMARY for
   store writes."

THIS IS A LEDGER-CORRUPTION BUG, NOT A UX PAPERCUT, and it should be read that
way. A whole design ticket was written into the store of a worktree that had
already landed -- so the work was recorded somewhere nothing reads, which is
indistinguishable from never having filed it. It then left a PHANTOM LEASE on
main that blocked new tickets until a human deleted the worktree by hand. Silent
write to the wrong place, plus a blocking artifact whose cause is invisible from
where the symptom appears.

CONFIRMED INDEPENDENTLY IN THIS REPO. This exact hazard is already recorded here
from a prior incident: a single `cd` into a worktree silently redirected land
verification, git log and git grep, and three conclusions were drawn against the
wrong tree. The environment makes it easy -- a tool call that enters a worktree
can leave the shell's cwd there for subsequent commands, so the redirect happens
without anyone choosing it. Apollo has now hit the same class from the ledger
side rather than the query side, which is what makes it worth fixing in the tool
rather than in a habit.

WHY cwd IS THE WRONG AUTHORITY FOR A STORE WRITE. Reading against the local root
is often right -- that is how a worktree checks its own state. But WRITING the
ticket store is a repo-global mutation: there is one real ledger, and it lives in
the primary. Resolving the write target from cwd means an incidental shell state
decides where global state is recorded. The two operations deserve different
resolution rules, and today they share one.

THE CONSUMER OFFERED TWO REMEDIES; THEY ARE NOT EQUIVALENT:
  (a) REFUSE to run ticket verbs from a worktree whose ticket is done. Narrow,
      catches their exact incident, and leaves the general hazard live -- a
      worktree whose ticket is still OPEN can misdirect a write just as easily.
  (b) ALWAYS RESOLVE THE PRIMARY FOR STORE WRITES. Addresses the class.
PREFER (b), with (a)'s check as a loud warning rather than the mechanism.

BUT VERIFY THIS FIRST, because it may be load-bearing: worktree-local ledger
writes appear to be DELIBERATE in places -- this repo routinely mirrors scope and
evidence from a worktree into main, which implies the worktree store is a real,
intended staging area. If so, (b) as stated would break the land flow. Establish
which ticket mutations are meant to be worktree-local staging and which are
meant to be global, and make that distinction explicit in the code rather than
emergent from cwd. THAT DISTINCTION IS THE ACTUAL DELIVERABLE; the cwd bug is
its symptom.

NOTE THE ADJACENT CONFIRMED DEFECT: T-3958 records that `ticket show`/`list`
read a stale root mirror after a worktree close. Same fault line -- two stores,
no stated rule about which is authoritative for which operation. Read them
together.

MUST-FIRE FIXTURE: a ticket-store WRITE issued with cwd inside a worktree lands
in the primary store (or is refused with a message naming both roots).
MUST-STAY-QUIET: the legitimate worktree-local staging writes the land flow
depends on still work.
THIRD FIXTURE: no phantom lease survives on main after a worktree is landed and
removed.

ACCEPTANCE
- An explicit, stated rule for which ticket mutations are worktree-local staging
  and which are global, verified against the existing mirror/land flow rather
  than assumed.
- Store writes resolve by that rule, not by cwd.
- All three fixtures committed.