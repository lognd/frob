---
id: T-4049
title: 'F-248: --ticket SCOPE findings are computed over the whole branch diff, so
  sibling tickets on a shared worktree contaminate each other'
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
- src/frob/gates/_tickets_gate.py
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
Consumer logand.app-v2 F-248, 2026-09-06:

  "Closing T-0228, T-0226 and T-0227 in ONE worktree on sub-15-web-shell (AS
   INSTRUCTED, to avoid re-symlinking node_modules three times) means the diff
   for any one of them includes the other two tickets' commits. `frob check
   --ticket T-0228 --base sub-15-web-shell` then flags SCOPE001/SCOPE002 for
   files genuinely in T-0226/T-0227's scope, not T-0228's -- because the gate has
   no way to attribute a touched file in the diff to the specific ticket that
   touched it (it only knows 'in T-0228's scope or not')."

THE GATE IS ASKING A ONE-TICKET QUESTION OF A MULTI-TICKET DIFF. `--ticket X`
promises a verdict about X. It computes that verdict over every commit between
the base and HEAD, and when a branch legitimately carries three tickets, two
thirds of the evidence belongs to somebody else. Every finding it produced here
was TRUE ABOUT THE DIFF AND FALSE ABOUT THE TICKET.

NOTE THE MULTI-TICKET WORKTREE WAS THE CORRECT CHOICE, not a shortcut. They
consolidated to avoid re-symlinking node_modules three times, and frob itself has
no objection to co-located tickets -- T-3958 records that the land path explicitly
supports a "co-located passenger ticket". So the tool supports the arrangement in
one subsystem and mis-reports it in another.

THEIR PROPOSED FIX IS THE RIGHT SHAPE AND IS CONCRETE: walk the commit list
between --base and HEAD, attribute each commit to a ticket via its trailer or
message (or the frob:ticket directives it touches), and flag a file as
out-of-scope for X only if X'S OWN COMMITS touched it. Note frob already writes
ticket-identifying commit messages on every ledger and land commit, so the
attribution key exists -- this is using information already in the history, not
inventing a new record.

VERIFY BEFORE BUILDING: does any existing code already attribute commits to
tickets this way? The land path reasons about which commits belong to a ticket
(it squashes them), and `frob verify`'s attribution engine exists. If either
already does commit-to-ticket attribution, this should consume it rather than
deriving a second answer -- two independent attribution mechanisms is precisely
the desync shape that produced three other defects filed today.

THIS IS THE FIFTH SCOPE-DENOMINATOR DEFECT, and the cluster now needs one owner
rather than five fixes:
  T-3978  a scope glob matching zero TRACKED files is accepted silently
  T-4004  SCOPE001/002 computed over the transitive import closure, so a ticket
          with an EMPTY diff is already in violation
  T-4002  subtractive scope mirroring destroys a sibling branch's scope
  T-4032  SCOPE001 fires on a gitignored symlink and on a ticket the run filed
  this    the diff denominator spans sibling tickets on a shared branch
All five are about WHAT SET scope is computed over -- the tracked-file universe,
the closure breadth, the branch's commit range, the mirroring direction. Whoever
takes any one must read the other four; five independent narrowings will
conflict, and a single coherent answer to "what is this ticket's subject set"
would likely resolve several at once.

DO NOT fix this by telling users not to share a worktree. That instruction would
contradict the land path's own support for co-located tickets, and the consumer
had a good reason (a costly per-worktree setup step).

MUST-FIRE FIXTURE: a file genuinely outside ticket X's scope, touched by X's OWN
commit, is still flagged.
MUST-STAY-QUIET: a file touched only by a SIBLING ticket's commit on the same
branch produces no finding for X.
THIRD FIXTURE: the single-ticket-per-branch case is byte-identical to today -- no
regression for the common shape.

ACCEPTANCE
- Whether commit-to-ticket attribution already exists, answered by grep first;
  reuse it if so.
- Findings for X derived only from X's own commits.
- Read against the other four denominator tickets, with a statement of whether a
  shared fix is possible.
- All three fixtures committed.