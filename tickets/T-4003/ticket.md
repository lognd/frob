---
id: T-4003
title: 'F-219: TEST002/TEST003 report 0 collected cases for tested TS symbols although
  the ts collector is wired (cache path unproven)'
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
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: F-225 reports the same zero on a second symbol class (plain .ts script entry
    points, pre-existing on prerender.ts), which widens the footprint and argues against
    a JSX/component-specific cause; recorded here rather than filed as a duplicate
  actor: logan
  at: '2026-09-06'
  old_length: 3789
  new_length: 5517
- mode: set
  reason: 'root cause found and verified (T-4016: the TS walker emits no symbol for
    describe/it call expressions); my cache/invalidation hypothesis is superseded,
    and this ticket is retained as the symptom to re-measure rather than closed on
    the cause landing'
  actor: logan
  at: '2026-09-06'
  old_length: 5517
  new_length: 7383
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2 F-219, 2026-09-06:

  "Landing.tsx::Landing and other symbols with frob:tests directives and a fresh
   `frob test` collection still show 0 collected unit case(s); the vitest
   collector does not feed this rule's cache. Same root cause as F-172."

THE SYMPTOM IS TRUSTED. THE STATED MECHANISM DOES NOT HOLD ON MAIN, AND THE
"same root cause as F-172" ATTRIBUTION IS ALMOST CERTAINLY WRONG. I checked
before filing, because I got the F-172 diagnosis wrong once already by accepting
a consumer's mechanism that matched a grep:

  - src/frob/gates/__init__.py:6367-6384 calls collect_python_tests,
    collect_rust_tests AND collect_ts_tests. All three feed collection.
  - The comment at :694-700 states TS was REMOVED from the "extensions frob
    parses but cannot collect executed evidence for" set by T-0730, because
    collect_ts_tests's vitest node ids are `path::name` symrefs -- the exact
    shape symref_to_nodeid already produces from a TS frob:tests directive, so
    _node_id_collected's exact/prefix match works the same as python and rust.

So TS is wired into TEST002/TEST003 on main by design and by an old ticket
(T-0730), not by today's work. F-172's cause was different: the evidence BINDING
path, fixed today by T-3925 (f96a36ae2). Do not assume this is the same defect.

TWO LIVE POSSIBILITIES, AND THE FIRST JOB IS TO SEPARATE THEM:
  1. STALE INSTALL. The consumer runs an installed frob reporting 0.530.0, and
     we now know (T-4001) that a released 0.530.0 and main's 0.530.0 can be
     different software. If their build predates something relevant, the report
     is about code we no longer have. THIS MUST BE RULED OUT FIRST -- ask for a
     build identity or reproduce against a clean install of their exact version.
  2. A CACHE PATH, WHICH IS WHAT THEIR OWN WORDING POINTS AT. They said the
     collector "does not feed this rule's CACHE" -- not that it is never called.
     Collection succeeding while the cache the rule reads stays stale is a
     different defect from the collector being unwired, and my check above does
     not rule it out. Trace how TEST002/TEST003's collected-id set is cached and
     invalidated, and whether `frob test` refreshes it for TS specifically. Note
     a related instance already recorded here: a stale collection cache produced
     a false COV003 finding in this repo (my floor read 4 vs a re-measure of 0).

THIS IS ALSO A SUBJECT-COUNT INSTANCE, which is the strongest reason to fix it
rather than explain it away. "0 collected unit case(s)" for a symbol that
demonstrably HAS tests is a rule reporting a number about a set it failed to
populate -- exactly what T-3985's subject-count primitive is meant to make
impossible to state silently. Whatever the cause turns out to be, the rule should
be able to distinguish "collected 0 cases from a populated collector" from
"collector returned nothing / was not consulted". Cross-reference T-3985 and
prefer a fix that makes the distinction visible rather than one that only
re-wires a call.

DO NOT close this as "already fixed" without a reproduction. That is the exact
error I made in the other direction on F-172 -- accepting a mechanism because one
grep agreed with it.

MUST-FIRE FIXTURE: a TS symbol with a frob:tests directive and a real vitest test
reports a non-zero collected count after a fresh collection.
MUST-STAY-QUIET: a TS symbol genuinely without tests still reports 0 and still
fires the rule.
THIRD FIXTURE: a stale cache cannot present as a genuine 0 -- the two are
distinguishable in the output.

ACCEPTANCE
- Stale-install ruled in or out FIRST, with the method stated.
- If real: the cache/invalidation path traced and named, not guessed.
- The zero made self-describing per T-3985.
- All three fixtures committed.
## SECOND SYMBOL CLASS, SAME DAY: F-225

  "Script entry points with frob:tests directives still report '0 collected unit
   case(s)' on frontend/scripts/*.ts (pre-existing on prerender.ts); same root
   cause as F-172/F-219 (vitest collection not feeding the rule)."

This widens the reported surface from React components (Landing.tsx) to plain TS
SCRIPT entry points, and notes it is PRE-EXISTING on prerender.ts rather than
newly introduced. Two different symbol shapes, same zero.

WHY THAT MATTERS FOR DIAGNOSIS RATHER THAN JUST VOLUME: a defect affecting both a
.tsx component and a plain .ts script argues against anything specific to JSX,
component detection, or a particular directive placement, and points at the
collection/caching path this ticket already names as the open question. It also
argues against the stale-install hypothesis being the WHOLE story -- pre-existing
on a second file class is a broader footprint than a single missed fix would
explain, though it still does not rule staleness out.

DO NOT treat the added instance as added evidence for their stated MECHANISM.
Their attribution is still "same root cause as F-172", and F-172's actual cause
(the evidence BINDING path, fixed by T-3925) is confirmed NOT to be this code
path -- TEST002/TEST003 call all three collectors at gates/__init__.py:6367-6384
and TS was deliberately admitted by T-0730. Two symptoms sharing a wrong
attribution are still one unproven mechanism.

The acceptance order above is unchanged: rule stale-install in or out FIRST, then
trace the cache/invalidation path. Use prerender.ts as the second reproduction
case -- a plain .ts script is a simpler subject than a .tsx component and is the
better one to bisect against.

## ROOT CAUSE FOUND -- MY CACHE HYPOTHESIS IS SUPERSEDED (T-4016)

The consumer filed F-230 and it is verified in our source:

    git grep -c "call_expression" -- src/frob/lang/_walk_typescript.py  ->  0

frob.lang._walk_typescript emits RawSymbols for function_declaration (:43),
class-member methods (:83) and top-level lexical_declaration constants (:107),
and has NO call-expression handling at all. `describe(...)` and `it(...)` are
call expressions, so a frob:tests directive above an `it()` has no enclosing
symbol to attach to and degrades to the bare file path -- which can never equal a
vitest node id.

SO BOTH OF MY EARLIER OBSERVATIONS WERE CORRECT AND NEITHER WAS THE ANSWER. I
verified that all three collectors are called (gates/__init__.py:6367-6384) and
that TS was deliberately admitted to TEST002/TEST003 by T-0730, and concluded the
remaining suspect was a cache/invalidation path. Collection is fine and the
collected ids are fine; the missing half is the OTHER side of the edge -- the
graph holds no symbol for the test, so there is nothing for a collected id to
match against. Stop chasing the cache.

IT ALSO EXPLAINS THE TWO-SYMBOL-CLASS SPREAD recorded above. F-219 (.tsx
components) and F-225 (plain .ts scripts) are one defect, because the failure is
not in the documented subject at all -- it is in the test symbol every TS
frob:tests directive must resolve to, which is absent for every vitest test in
every TS file.

THIS TICKET STAYS OPEN, deliberately: T-4016 fixes the walker, and this one is
the SYMPTOM that must be RE-MEASURED against that fix before either is closed.
Do not close this on the strength of T-4016 landing -- that would repeat the
mistake of declaring a symptom fixed because a plausible cause was addressed. The
stale-install question above is also still unresolved and remains worth ruling
out independently.
