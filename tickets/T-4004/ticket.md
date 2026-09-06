---
id: T-4004
title: 'F-218: SCOPE001/002 compute over the transitive import closure, so a ticket
  with an EMPTY diff is already in violation'
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
Consumer logand.app-v2 F-218, 2026-09-06:

  "T-0032's first `frob check --ticket` run, BEFORE ANY COMMIT, already flagged
   .gitignore, ci.yml and package.json through the transitive import closure of
   the scoped pages. SCOPE001/002 should be computed over the diff's files (and
   their direct frob:doc/frob:tests targets), not the reachability closure."

NOTE THE DECISIVE DETAIL: before any commit. The ticket had changed NOTHING and
was already in violation. A scope gate that fires on an empty diff is not
measuring the ticket's work; it is measuring the shape of the import graph.

THE PRINTED NOTE CONTRADICTS THE BEHAVIOUR, which is what makes this worse than
an over-broad default. They report the output claims findings are diff-scoped
while the computation walks the transitive import closure. A message that
misdescribes what a rule did is its own defect: it tells the user the finding is
about their change, so they go looking for a change that does not exist. This
repo has a standing instance of the same shape -- intent stated in prose that the
code does not enforce -- and it costs a debugging session every time.

THE CLOSURE IS THE WRONG DENOMINATOR FOR A REACT APP, and probably for anything
with a dense import graph. Transitive reachability from a few page components
reaches configuration and build files (.gitignore, ci.yml, package.json) that no
reasonable person would call in scope for a page ticket. The consumer's proposed
denominator -- the diff's files plus their DIRECT frob:doc/frob:tests targets --
is the right shape: it is bounded, it is what scope actually means, and it does
not grow with the app.

CROSS-CHECK BEFORE CHANGING ANYTHING, because there is a real tension: scope
closure exists to catch the case where a ticket edits a file whose doc/test
partners live elsewhere, and this repo's own filings routinely emit dozens of
closure warnings that ARE useful (a recent scope --add printed 84). So the fix is
not "delete the closure". Determine which findings need the transitive walk and
which need only the direct edges, and confirm the direct-edge set still catches
the case closure was introduced for.

RELATED, READ TOGETHER: T-3943 (F-173) found the diff BASE hardcoded to main, so
a ticket on a branch behind main saw 439 findings where 8 were real. That is the
same failure mode -- SCOPE/COV findings computed over the wrong denominator and
reported as if they were about the ticket -- reached from the base-ref side
rather than the closure side. If both land independently they will fight; whoever
takes this should check T-3943's state first.

ALSO WORTH MEASURING WHILE HERE: whether closure cost explains T-3993 (ledger
verbs running for minutes in silence). If the transitive walk is the dominant
cost of `ticket new`/`scope --add`, narrowing the denominator fixes a correctness
problem and a performance problem with one change.

MUST-FIRE FIXTURE: a ticket whose diff genuinely omits a file it edits is still
flagged.
MUST-STAY-QUIET: a ticket with an EMPTY diff produces no SCOPE001/002 findings at
all -- the reported case, and the cleanest possible statement of the bug.
THIRD FIXTURE: the printed note matches what was actually computed.

ACCEPTANCE
- Denominator narrowed to the diff plus direct doc/test edges, with evidence
  that the case closure was built for is still caught.
- The output's description of its own scoping made accurate.
- Checked against T-3943 so the two fixes do not conflict.
- All three fixtures committed.