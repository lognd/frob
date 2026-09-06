---
id: T-4125
title: a land refused on type errors reproducible in no tree the operator can inspect,
  reporting a bare count with no lines and no statement of which tree it checked
state: queued
kind: bug
origin: agent
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
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a land refused by the type stage, when the refusal is printed, then
    it names each error's file, line and text, plus which tree was checked and the
    commit it was composed against
  evidence: []
- text: given a genuine new type error in the ticket's own touched files, when the
    land runs, then it is still refused
  evidence: []
- text: given a type error present before the merge with the target branch but absent
    after it, when the land runs, then the land is not refused
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A LAND REFUSED ON TYPE ERRORS THAT DO NOT EXIST IN ANY TREE THE OPERATOR CAN
INSPECT, AND NAMED NO LINES. Reported as logand.app-v2 F-311. The land reported
that the type checker found 2 NEW errors in the ticket's own touched files, and:

  - the message named NO line numbers and NO error text, only a count
  - running the type checker on the worktree was clean
  - running it after merging main was clean
  - the retry, after merging main, LANDED

So the operator was refused by a measurement they could not reproduce, could not
locate, and could not argue with. They guessed at the cause -- the land's type
stage running on the pre-land canonicalised tree before the merge with main,
which carried a sibling ticket's edits to the same test module, or against a
different checker config -- and their guess is plausible, but the point is that
GUESSING WAS THE ONLY OPTION AVAILABLE TO THEM.

THE DIAGNOSTIC GAP IS THE PRIMARY DEFECT AND SHOULD BE FIXED FIRST, independently
of whatever the underlying tree-selection bug turns out to be. A refusal that
reports a count without the findings is unfalsifiable: it cannot be confirmed,
cannot be reproduced, and cannot be shown to be wrong. The operator's only
recourse is to retry and hope, which is exactly what happened -- and a retry that
succeeds teaches that land refusals are noise to be retried past. That is the
same wrong lesson the scaffold-noise ticket in this queue is about, arriving
through a different door.

WHAT THE MESSAGE MUST CARRY, and this is cheap because the checker already
produced it:
  - the file and line of each error, and its text
  - WHICH TREE was checked, named explicitly: the worktree as written, the
    canonicalised pre-land tree, or the post-merge tree
  - the base or merge commit that tree was composed against
The consumer asked for the first two by name. The third is what makes the report
reproducible by hand.

THE UNDERLYING BUG IS SECONDARY BUT REAL, AND THIS REPO HAS THE SHAPE ON FILE.
Our own record already establishes that a land-time check can read a pre-merge
tree rather than the tree that will actually land, and that a check reading the
wrong tree can fail in either direction. Two candidate mechanisms, both worth
distinguishing rather than assuming:

  (a) The stage checks a tree composed BEFORE the merge with the target branch.
      A sibling ticket's landed edits to the same module are then absent, so a
      reference that resolves after the merge does not resolve before it. This
      matches the consumer's report exactly: their sibling ticket had edited the
      same test module.
  (b) The stage runs with a different checker configuration than a direct
      invocation does. This would make the two measurements incomparable
      regardless of tree.

DETERMINE WHICH BEFORE FIXING EITHER. They need different repairs, and a fix for
(a) applied to a (b) failure would leave the defect in place while looking
resolved.

DO NOT FIX THIS BY RELAXING THE GATE. A pre-merge check that refuses too much is
a bug; a land that stops checking types is worse. If the check must move to the
post-merge tree to be correct, move it -- do not weaken it in place.

MUST-FIRE FIXTURE:   a land refused by the type stage names every error's file,
                     line and text, and names which tree it checked.
MUST-STAY-QUIET:     a land with a genuine new type error in its own touched
                     files is still refused -- the diagnostic improvement must
                     not become a downgrade to a warning.
THIRD FIXTURE:       an error that exists only before the merge with the target
                     branch, and not after, does not refuse the land.

ACCEPTANCE
- The refusal message carries file, line, text, the tree checked, and the commit
  that tree was composed against.
- Mechanism (a) versus (b) determined by measurement and stated.
- The gate is not weakened; if the check moves trees, say which and why.
- All three fixtures committed.
