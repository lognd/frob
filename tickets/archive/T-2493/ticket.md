---
id: T-2493
title: waive-audit has no systematic INERT-waiver check (path/symbol-shape mismatch)
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_waive_audit.py
- tests/unit/test_waive_audit_runner.py
- docs/modules/app.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_waive_audit_runner.py
  reason: add tests for the new collision-check function and document it alongside
    the rest of waive-audit in the same doc anchor
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/app.md
  reason: add tests for the new collision-check function and document it alongside
    the rest of waive-audit in the same doc anchor
  actor: logan
  at: '2026-08-18'
body_changes:
- mode: append
  reason: 'T-2493: collision-based INERT-waiver detection. T-1579 asked for

    exactly this shape of feature once already -- "let the audit tell us a

    waiver is doing nothing" -- and the version that shipped

    (_rule_has_live_finding, frob.gates._fix_engine_sync) reasoned "the

    rule fired somewhere in this run, so the detector is healthy, so a

    waiver of that rule matching nothing here is provably stale." That

    reasoning is UNSOUND: it proves the detector produced output

    SOMEWHERE, never that it re-examined the ONE site a given waiver

    covers. It shipped, and during a real land it deleted 55 LIVE waivers

    during a partially-degraded run that still found some instances of a

    rule while missing the exact sites those waivers covered. Reverted;

    tests/gates_suite/test_waive.py::TestWaive004DegradedRunGuard::test_mass_invalidation_with_live_finding_elsewhere_still_refuses

    locks against reintroducing it. T-1904 (successor) established that a

    SOUND escape needs per-site analysis-coverage proof, which is a

    materially larger capability than a guard tweak -- built later as

    T-1921/T-1943''s frob.gates._coverage_sites, and even THAT substrate was

    deliberately shipped wired to nothing (its own module docstring: "NOT

    WIRED INTO WAIVE004 (or any other auto-fix/waiver-retirement path) by

    this ticket").


    This is the general form of the two REAL matching bugs this repo has

    actually found and fixed this way already: T-2314 (gate:PERF emitted

    absolute file paths, so _match_waiver''s file-equality check silently

    never matched -- caught because a KNOWN-waived site''s finding kept

    showing up unsuppressed) and T-2438 (a hand-rolled C++ symref spelling

    differed from the DSL''s own qualname join, so the symbol-exact match

    silently missed -- same shape: a violation persisted despite a waiver

    that should have covered it). Both were found by noticing presence,

    never absence.


    WHAT THIS DELIBERATELY DOES NOT CATCH, disclosed rather than hidden: a

    waiver whose site has ZERO current violations of its rule ANYWHERE in

    the tree -- the "hardened guard, currently quiet" case a real

    load-bearing waiver looks exactly like. find_collision_suspects cannot

    tell that case apart from a genuinely-inert waiver, and does not try

    to -- it reports NOTHING for either, by construction, because there is

    no active violation to collide with in either case. Closing that gap

    requires the per-site analysis-coverage proof T-1904 named as the

    missing capability (confirm the exact site was actually re-examined

    this run before treating its silence as meaningful), which

    frob.gates._coverage_sites (T-1921/T-1943) only provides for five gate

    families and was explicitly left unwired everywhere -- extending it

    into a general per-waiver inertness verdict is a materially larger,

    multi-file capability outside this ticket''s single-file scope, not

    something safe to approximate here with a heuristic.'
  actor: logan
  at: '2026-09-19'
  old_length: 1521
  new_length: 4957
evidence:
- tests/unit/test_waive_audit_runner.py::TestCollisionSuspects::test_active_unsuppressed_violation_in_same_rule_and_file_is_flagged
- tests/unit/test_waive_audit_runner.py::TestCollisionSuspects::test_a_correctly_matching_live_waiver_is_not_flagged
- tests/unit/test_waive_audit_runner.py::TestCollisionSuspects::test_a_quiet_hardened_site_with_zero_violations_anywhere_is_not_flagged
- tests/unit/test_waive_audit_runner.py::TestCollisionSuspects::test_absolute_violation_path_still_matches_repo_relative_waiver
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: f2fea5ae01caa3e71ca7dfda2da75309a4275423
---
Noted twice now in T-1614's own live passes (this session, both the pre-T-2485 attempt and this post-fix pass): 'no INERT waivers spotted' is reported for every reviewed batch, but that claim is weaker than 'none present' -- no systematic check runs. An INERT waiver (T-2314's 116 path-shape mismatches, T-2438's symbol-spelling one) reads as honoured to anyone grepping while doing nothing, and it will not show up as a NEEDS_REVIEW finding in waive-audit scan's current shape, because scan only lists waivers that MATCHED a live finding at their site -- a waiver that never matches anything (wrong path shape, wrong symbol, stale line number after a refactor) produces no violation to attach the waiver to in the first place, so it is invisible to this whole mechanism by construction, not merely unreviewed. Recommend: a companion check that, for every frob:waive directive in the source, confirms the named rule's detector actually fires (or would fire, absent the waiver) at that exact site -- i.e. walk the un-waived violation set the gate would produce and confirm every declared frob:waive has a corresponding suppressed violation, flagging any waiver with zero corresponding matches as INERT. This is a different check from waive-audit's honesty audit (which judges REASON quality) -- it judges whether the waiver DOES ANYTHING at all. Filed rather than designed/built here since T-1614's own declared scope this pass is empty (audit only, no source changes beyond the two obsolete-waiver removals already done).

<!-- narrative-moved:src/frob/app/ticket_runner/_waive_audit.py:756:T-2493 -->
---------------------------------------------------------------------------
T-2493: collision-based INERT-waiver detection.

READ THIS BEFORE TOUCHING ANYTHING BELOW. T-1579 asked for exactly this
shape of feature once already -- "let the audit tell us a waiver is
doing nothing" -- and the version that shipped
(`_rule_has_live_finding`, `frob.gates._fix_engine_sync`) reasoned "the
rule fired somewhere in this run, so the detector is healthy, so a
waiver of that rule matching nothing here is provably stale." That
reasoning is UNSOUND: it proves the detector produced output
SOMEWHERE, never that it re-examined the ONE site a given waiver
covers. It shipped, and during a real land it deleted 55 LIVE waivers
during a partially-degraded run that still found some instances of a
rule while missing the exact sites those waivers covered. Reverted;
`tests/gates_suite/test_waive.py::TestWaive004DegradedRunGuard::
test_mass_invalidation_with_live_finding_elsewhere_still_refuses` locks
against reintroducing it. T-1904 (successor) established that a SOUND
escape needs per-site analysis-coverage proof, which is a materially
larger capability than a guard tweak -- built later as T-1921/T-1943's
`frob.gates._coverage_sites`, and even THAT substrate was deliberately
shipped wired to nothing (its own module docstring: "NOT WIRED INTO
WAIVE004 (or any other auto-fix/waiver-retirement path) by this
ticket").

counter-example. This is the general form of the two REAL matching
bugs this repo has actually found and fixed this way already: T-2314
(`gate:PERF` emitted absolute file paths, so `_match_waiver`'s
file-equality check silently never matched -- caught because a
KNOWN-waived site's finding kept showing up unsuppressed) and T-2438
(a hand-rolled C++ symref spelling differed from the DSL's own
qualname join, so the symbol-exact match silently missed -- same
shape: a violation persisted despite a waiver that should have covered
it). Both were found by noticing presence, never absence.

WHAT THIS DELIBERATELY DOES NOT CATCH, disclosed rather than hidden: a
waiver whose site has ZERO current violations of its rule ANYWHERE in
the tree -- the "hardened guard, currently quiet" case a real load-
bearing waiver looks exactly like. `find_collision_suspects` cannot
tell that case apart from a genuinely-inert waiver, and does not try
to -- it reports NOTHING for either, by construction, because there is
no active violation to collide with in either case. Closing that gap
requires the per-site analysis-coverage proof T-1904 named as the
missing capability (confirm the exact site was actually re-examined
this run before treating its silence as meaningful), which
`frob.gates._coverage_sites` (T-1921/T-1943) only provides for five
gate families and was explicitly left unwired everywhere -- extending
it into a general per-waiver inertness verdict is a materially larger,
multi-file capability outside this ticket's single-file scope, not
something safe to approximate here with a heuristic.

with its own scope and its own review) decides what to do with a
reported collision. The `AuditVerdict.CLEAN` reachability rule
elsewhere in this module (only `complete`, never `scan`, can claim
CLEAN) applies here too, transitively: a collision-suspect report is
evidence for a human/agent classifying per T-1614's rubric, not itself
a verdict.