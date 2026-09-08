---
id: T-4298
title: nothing on the land path checks repo-wide formatting, so drift accumulates
  faster than release tickets clear it
state: queued
kind: bug
origin: human
created: '2026-09-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_land_format.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/_land.py
  reason: avoid scope collision with in-progress T-4281's lease on _land.py; land-path
    gates are wired via gates/__init__.py, so the new whole-diff formatting gate belongs
    in a new module registered there instead
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/gates/__init__.py
  reason: avoid scope collision with in-progress T-4281's lease on _land.py; land-path
    gates are wired via gates/__init__.py, so the new whole-diff formatting gate belongs
    in a new module registered there instead
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/gates/_land_format.py
  reason: avoid scope collision with in-progress T-4281's lease on _land.py; land-path
    gates are wired via gates/__init__.py, so the new whole-diff formatting gate belongs
    in a new module registered there instead
  actor: logan
  at: '2026-09-08'
designated_repro_test: null
acceptance:
- text: given a land whose changed files include one the formatter would rewrite,
    when the land runs, then the drift is either refused with attribution or applied
    automatically, rather than reaching the integration branch unnoticed
  evidence: []
- text: given the current drift, when it is cleared, then that mechanical rewrite
    is a separate commit from the mechanism change and the report names the count
    actually found rather than a count quoted from this ticket
  evidence: []
- text: given the choice between refusing and rewriting, when the fix lands, then
    which was chosen and why is recorded where the next reader will find it
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
NOTHING ON THE LAND PATH CHECKS REPO-WIDE FORMATTING, SO EVERY LAND CAN ADD DRIFT
THAT ONLY THE INTEGRATION RUN CATCHES -- AND IT IS ACCUMULATING FASTER THAN IT IS
BEING CLEARED.

MEASURED TODAY, TWICE. The first self-gate run this tree ever completed reported
four files the formatter would rewrite. A ticket was filed and landed to clear
exactly those four. Immediately afterwards, a fresh check of the working tree
reports SIX files needing reformatting -- more than before the fix -- because
several lands in between introduced new drift of their own. Clearing the count is
therefore not a fix; the count refills.

WHY THE EXISTING GATE DOES NOT CATCH THIS, AND IT IS BY DESIGN RATHER THAN BY
ACCIDENT. The formatting gate this project runs on the land path examines only
the directive-comment lines touched by the current diff. Its own scope note says
so plainly: it never scans the whole tree and is not a general formatter check, and
a clean result from it does NOT mean the repository is formatter-clean. That note
is honest and correct. The problem is that nothing else on the land path covers
what it deliberately excludes, so the honest disclaimer has become a gap.

THE CONSEQUENCE IS A RELEASE-BLOCKING GATE THAT ONLY FAILS AFTER THE FACT. The
integration run does check the whole tree, so drift surfaces there -- minutes to
an hour after the land that caused it, attributed to nobody in particular, and
mixed in with whatever else that run found. Whoever is driving the release then
files a ticket to clear a count that has already moved on. That is a treadmill,
not a check.

WHAT THE FIX SHOULD DO. Make the land path answer the same question the
integration run asks, for the files that land is actually touching. A land should
not be able to introduce a file the formatter would rewrite. Prefer checking the
land's own changed files over scanning the whole tree on every land, so the cost
stays proportional and the attribution stays exact -- the person who introduced
the drift is the one told about it, while it is still cheap to fix.

CONSIDER WHETHER FORMATTING SHOULD SIMPLY BE APPLIED RATHER THAN REPORTED. This
project already has a formatting verb and already runs automatic fixes on the
land path for other rule families. If applying the formatter to the land's own
changed files is safe and deterministic -- and formatters are chosen precisely
because they are -- then refusing a land over formatting is friction where a
rewrite would do. Decide deliberately and record which was chosen and why.

CLEAR THE CURRENT DRIFT AS PART OF THIS, and commit that as its own change so the
mechanical rewrite stays separable from the mechanism change. Expect the exact
file count to differ by the time you run it; report what you actually found rather
than the six named here.
