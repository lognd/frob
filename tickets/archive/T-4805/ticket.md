---
id: T-4805
title: SCOPE002 emits 587 scope-closure warnings on a ticket with EMPTY scope; scope
  closure must be computed against the ticket's declared scope only
state: done
kind: bug
origin: agent
created: '2026-09-19'
priority: high
parent: T-4127
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_new.py
- tests/unit/test_scope_closure_declared_scope_only.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: T-4665
  new_value: T-4127
  reason: '2026-09-19: coordinator amendment -- T-4127 is the standing record of the
    SCOPE002 hub-file explosion and is this leaf''s parent record; T-4127 is itself
    a child of story B (T-4665), so T-4805 remains under story B transitively'
  actor: logan
  at: '2026-09-19'
evidence:
- tests/unit/test_scope_closure_declared_scope_only.py::TestEmptyScopeIsZeroWarnings::test_empty_scope_emits_zero_warnings_even_with_hub_file_gaps
- tests/unit/test_scope_closure_declared_scope_only.py::TestDeclaredScopeOnlyFiltering::test_three_file_scope_keeps_only_matching_gaps
- tests/unit/test_scope_closure_declared_scope_only.py::TestDeclaredScopeOnlyFiltering::test_scope_actually_covering_the_hub_file_still_gets_its_warnings
designated_repro_test: tests/unit/test_scope_closure_declared_scope_only.py::TestEmptyScopeIsZeroWarnings::test_empty_scope_emits_zero_warnings_even_with_hub_file_gaps
acceptance:
- text: Given filing a ticket with an EMPTY declared scope emits 587 scope-closure
    warnings at HEAD c8f56ef10 (measured twice on 2026-09-19 while filing T-4662 and
    T-4668), every one naming a design/frob.strata frob:doc edge the ticket does not
    touch, when this lands, then a test asserts an empty-scope ticket emits ZERO scope-closure
    warnings -- a positive control that fails today.
  evidence:
  - tests/unit/test_scope_closure_declared_scope_only.py::TestEmptyScopeIsZeroWarnings::test_empty_scope_emits_zero_warnings_even_with_hub_file_gaps
  - tests/unit/test_scope_closure_declared_scope_only.py::TestDeclaredScopeOnlyFiltering::test_three_file_scope_keeps_only_matching_gaps
  - tests/unit/test_scope_closure_declared_scope_only.py::TestDeclaredScopeOnlyFiltering::test_scope_actually_covering_the_hub_file_still_gets_its_warnings
- text: Given the fix must not be 'disable the check', which would void the owner's
    both-ways scope-closure directive, when a ticket declares N specific files, then
    a test asserts warnings are emitted ONLY for doc edges reachable from those N
    files, and still are emitted for those.
  evidence:
  - tests/unit/test_scope_closure_declared_scope_only.py::TestDeclaredScopeOnlyFiltering::test_three_file_scope_keeps_only_matching_gaps
  - tests/unit/test_scope_closure_declared_scope_only.py::TestDeclaredScopeOnlyFiltering::test_scope_actually_covering_the_hub_file_still_gets_its_warnings
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
SF-18 (MEDIUM). Leaf of story B (T-4665) under epic T-4662. Story points: 2.
IMMEDIATELY DISPATCHABLE -- no blockers.

PARENT RECORD: **T-4127** "SCOPE002 explodes on hub files (design/frob.strata,
docs/modules/gates.md)" is the standing record of this finding and carries the
three original measurements. This leaf is the actionable slice of it, promoted
out of an attachment by the coordinator on 2026-09-19 because the finding is
sharper than T-4127 states and can be fixed without waiting on the hub-file
question.

THE MEASUREMENT THAT PROMOTED IT, taken by the planner while filing epic T-4662
on 2026-09-19 (not from the audit -- fresh, and reproducible by filing any
ticket):

    frob ticket new ... (EMPTY scope, --declare-no-scope, touches no files)
    -> 587 scope-closure warnings
    -> "579 more warning(s) collapsed -- set FROB_SCOPE_CLOSURE_VERBOSE=1
        and retry to see all 587"

Every one named a `design/frob.strata::<node>` frob:doc target resolving into
`docs/strata/roadmap.md` or `docs/guides/claude-hooks.md`, e.g.:

    scope closure: design/frob.strata::frob's frob:doc target lives in
    'docs/strata/roadmap.md', not in scope -- consider --add 'docs/strata/roadmap.md'

The identical 587 fired again on T-4668, whose declared scope is three files,
none of them design/frob.strata.

WHY THAT IS A DIFFERENT AND WORSE FINDING THAN T-4127 RECORDS
T-4127's three measurements (140, 345 and 71 on 2026-09-06, by three independent
agents) were all taken by agents who were TOUCHING a hub file. This one was not:
a ticket with NO declared scope at all, touching nothing, drew 587 warnings about
a file it does not name. So "only tickets that touch design/frob.strata are
affected" is not a true statement about current behaviour, and the fix cannot be
limited to hub-file granularity. Scope closure is evidently being computed over
the whole repo's doc edges rather than over the ticket's declared scope.

Corroboration from the audit (SF-18): scratchpad/why-T-4111.txt:154-155 records
"Scope-closure WARN noise on design/frob.strata (500+ doc-anchor
cross-references)"; CHANGELOG T-3884 discloses it as known debt, "hundreds of
unrelated symbols (docs/strata/roadmap.md alone describes 134), none of which
this ticket touches"; 88 ticket.md files under tickets/ mention SCOPE002.

THE FIX
Scope closure must be computed against the TICKET'S DECLARED SCOPE ONLY. A
ticket that declares no scope has nothing to close over and must emit nothing. A
ticket that declares three files must be told only about doc edges reachable
from those three files -- never about every frob:doc edge in the repository.

Per memory/guard-design-lessons.md, a guard that cries wolf is already broken:
587 warnings that no agent can act on are not a safety net, they are the reason
nobody reads scope-closure output at all. And per the owner's scope-closure
directive (memory/scope-closure-directive.md), scopes are validated by doc-edge
and code-edge closure BOTH WAYS -- narrowing to the declared scope must preserve
that bidirectional check for the files actually in scope, not silence it.

POSITIVE CONTROL (the test that fails today)
Filing a ticket with an EMPTY declared scope emits ZERO scope-closure warnings.
It fails at HEAD c8f56ef10 with 587, reproducibly, on every `frob ticket new`.
Add a second test: a ticket declaring N specific files emits warnings ONLY for
doc edges reachable from those N files -- the negative control that stops this
being fixed by disabling the check outright, which would silently void the
owner's both-ways closure directive.