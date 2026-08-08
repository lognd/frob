---
id: T-1817
title: PRE001/SCOPE001 fire by construction on an unscoped check from a clean root,
  so the 0-error floor cannot be measured
state: queued
kind: bug
origin: human
created: '2026-08-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_scope.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
An unscoped `frob check` from a CLEAN root reports 2 errors that mean
nothing:

    PRE001: diff touches 4 file(s) but no active ticket is derivable
            (pass --ticket or use a T-####-name branch)
    SCOPE001: diff touches 4 file(s) but no active ticket is derivable

`git status --porcelain` in root is EMPTY at the time. The "diff" being
measured is against a baseline, not the working tree, and no active
ticket exists because a coordinator running a repo-wide check by
definition is not working a ticket.

WHY THIS IS A REAL DEFECT AND NOT COSMETIC: "main is at 0 errors" is
this repo's stated floor, and `frob check` unscoped from root is the
canonical way to measure it. That measurement currently cannot return 0
from a clean tree. Every reader must know to mentally discount exactly
these two, which means the floor is verifiable only by someone who
already knows the answer. A gate that fires by construction on its own
canonical invocation trains readers to discount it -- and a discounted
gate stops being read at all, which is how the two REAL errors this
session (ARCH001 and an invalid-return-type, both introduced by lands
that passed their own scoped checks) sat unnoticed on main.

This has already produced a concrete misread. An agent reported "0
errors" from within its worktree while the coordinator's unscoped run
showed 2; both were right, and reconciling them cost a round trip.

REQUIRED:

1. PRE001/SCOPE001 must not fire when no ticket is derivable AND the
   invocation is unscoped. That combination is not a violation -- it is
   the normal shape of a repo-wide audit. Either suppress them, or
   report them at note severity with a different code meaning "not
   evaluated", never `error`.
2. Whatever "diff touches 4 file(s)" is comparing against must be named
   in the message. From a clean tree the number is unexplainable, and an
   unexplainable count in an error message is what makes people stop
   reading the message.
3. Sibling to T-1804, which fixed the deferred sweep FILING spurious
   PRE001/SCOPE001 regression tickets from exactly this shape. That fix
   stopped the tickets; the underlying by-construction firing is still
   here. Fixing the symptom and leaving the cause is why this resurfaced.

Prefer suppression over a new flag. A `--i-am-not-working-a-ticket`
escape hatch would be a mechanism to manage a rule that should not have
fired, and the standing directive on this repo is to delete the rule's
bad case rather than add machinery around it.
