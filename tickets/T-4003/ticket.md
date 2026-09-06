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