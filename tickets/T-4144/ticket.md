---
id: T-4144
title: 'command evidence is refused when any python file sits in a ticket''s scope,
  even if the ticket''s diff touches none: the rule keys on scope contents rather
  than the touched set'
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a bug-kind ticket whose diff touches only non-code files, when it binds
    command evidence with an unrelated python file in its declared scope, then the
    binding is accepted
  evidence: []
- text: given a bug-kind ticket whose diff touches python, when it binds only command
    evidence, then it is still refused
  evidence: []
- text: given a ticket whose touched set cannot be determined, when the exemption
    is evaluated, then it is not widened
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A TICKET WHOSE CHANGE IS ENTIRELY NON-CODE CANNOT USE COMMAND EVIDENCE IF ANY
PYTHON FILE APPEARS ANYWHERE IN ITS DECLARED SCOPE, even when the diff never
touches it. The rule keys on what the SCOPE CONTAINS rather than on what the
TICKET CHANGED.

MEASURED, from logand.app-v2's corrected F-346 with their exact ticket list. Of
seven tickets rebinding generated-file evidence:

    T-0201, T-0279, T-0301, T-0303   kind=docs      accepted cmd evidence
    T-0225 (feature), T-0304 (bug), T-0323 (bug)    REFUSED, EvidenceKindNotAllowed

The three refusals all needed `scripts/vmodel_gen.py` in scope for a path check.
Their actual change was a spec row in a generated model file -- no python was
touched. Adding one python path to scope, for a reason unrelated to the change,
removed the exemption.

THE CODE IS BEHAVING AS DESIGNED, AND THE DESIGN HAS THE WRONG SUBJECT. The
escape hatch is `scope_has_python_surface(root, scope)` at
src/frob/tickets/_models.py:211, and its own docstring is explicit that it asks
whether "any file under `scope`" is a python file. The intent it documents is
right: a ticket that structurally cannot satisfy the coverage requirement via a
real test edge must have some other route to close. But scope is not the diff.
Scope is a LEASE and a coverage declaration; it routinely contains files a given
ticket reads, guards, or must not conflict on, and never edits.

THE SAME SUBJECT ERROR IS ALREADY OPEN ON ANOTHER RULE, and seeing the pair
together is the reason to fix them with one idea rather than two patches. T-4127
records that scope closure evaluates every symbol in a scoped FILE rather than
the symbols the diff actually touches, producing explosions of 140, 345 and 71
findings in three independent measurements. Both rules take "the ticket's scope"
where "what this ticket changed" is the honest subject. Whoever fixes either
should look at the other; if there is a shared helper answering "what did this
ticket actually touch", both should use it.

THIS ALSO CONTRADICTS THE HATCH'S OWN STATED PURPOSE. The docstring says the
hatch exists because such a ticket "structurally cannot ever satisfy D-02 via a
real TESTS edge or a scope-file match either". That is exactly as true for these
three tickets as for the docs-kind ones that passed -- their change has no python
to test. The presence of an unrelated python path in scope does not create a
testable surface for a spec-row edit; it only makes the check think one exists.

NOTE WHAT THE CONSUMER OFFERED AND WHY I AM NOT TAKING IT. They suggested their
filing habit might be at fault -- that docs-shaped bugs should be filed as
kind=docs. Do not adopt that as the fix. A generated-file or spec-row defect IS a
bug; relabelling it to satisfy an evidence rule corrupts the kind field, which
other rules and every future query depend on. A rule that pressures accurate
metadata into inaccurate metadata to let work close is the wrong-incentive class.

WHAT TO DO
  1. Decide the honest subject and say which you chose: the ticket's diff
     (what it changed) versus its scope (what it declared). Prefer the diff. If
     the diff is unavailable at the point the check runs, say so -- that is a
     real constraint and it changes the fix.
  2. Keep the conservative default the docstring already argues for: when the
     touched set cannot be measured at all, do NOT widen the exemption.
     Unmeasurable must never mean permitted.
  3. Check the OTHER direction too: a ticket that DOES touch python but binds
     only command evidence should still be refused. This fix must narrow the
     false refusals without opening a hole.

MUST-FIRE FIXTURE:   a bug-kind ticket whose diff touches only non-code files
                     may bind command evidence, even though an unrelated python
                     file sits in its declared scope.
MUST-STAY-QUIET:     a bug-kind ticket whose diff DOES touch python is still
                     refused command-only evidence, exactly as today.
THIRD FIXTURE:       when the touched set cannot be determined, the exemption is
                     NOT widened -- unmeasurable stays refused.

ACCEPTANCE
- The rule's subject changed from scope contents to the ticket's touched set, or
  the reason it cannot be is recorded.
- The unmeasurable case still refuses.
- The touch-python-but-bind-cmd-only case still refuses.
- The relationship to T-4127's identical subject error stated, and a shared
  helper used if one is warranted.
- All three fixtures committed.
