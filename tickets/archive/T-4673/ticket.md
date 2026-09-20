---
id: T-4673
title: 'SF-11: require_analyzable WARNs on every single design load -- 570 occurrences
  across 45 land logs, ~12.7 per land'
state: done
kind: bug
origin: agent
created: '2026-09-19'
priority: medium
parent: T-4665
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_packs.py
- tests/unit/strata/test_packs_analyzable_warning.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/strata/test_packs_analyzable_warning.py::TestAnalyzableWarningDeduped::test_load_design_ids_twice_warns_once
- tests/unit/strata/test_packs_analyzable_warning.py::TestAnalyzableWarningDeduped::test_first_call_still_warns
designated_repro_test: null
acceptance:
- text: Given src/frob/strata/_packs.py:96-102 emits a WARNING on every elaboration
    because frob's own model has trusted nodes and never declares std.policy.analyzable
    (the policy keyword appears 0 times in design/frob.strata), when this lands, then
    a test calling load_design_ids twice in one process asserts at most ONE such warning
    record -- a positive control that fails at HEAD c8f56ef10 with one per call.
  evidence:
  - tests/unit/strata/test_packs_analyzable_warning.py::TestAnalyzableWarningDeduped::test_load_design_ids_twice_warns_once
- text: Given demoting to DEBUG would destroy the signal the docstring deliberately
    chose, when this lands, then a second test asserts the FIRST warning is still
    emitted.
  evidence:
  - tests/unit/strata/test_packs_analyzable_warning.py::TestAnalyzableWarningDeduped::test_first_call_still_warns
threat: null
component: strata
anchor: false
anchor_reason: null
land_commit: null
---
SF-11 (MEDIUM). Leaf of story B (T-4665) under epic T-4662. Story points: 1.
IMMEDIATELY DISPATCHABLE -- no blockers.

EVIDENCE, re-read by the planner at src/frob/strata/_packs.py:96-102,
`require_analyzable`:

    if has_trusted and not already_present:
        _log.warning(
            "module %s: trusted component present without %s; "
            "auto-injecting mandatory base pack",
            module.name,
            ANALYZABLE_POLICY_ID,
        )

frob's own model has trusted nodes and does not declare std.policy.analyzable --
the `policy` keyword appears ZERO times in design/frob.strata (see SF-09's dead
keyword list). So this fires on EVERY elaboration. Counted across the 45
/tmp/land-T-*.log files: 570 occurrences, ~12.7 per land, i.e. once per
load_design_ids call site per run (SF-20 / leaf A2 lists the 7 call sites). It
is the first thing printed by a bare load_design_ids call.

The docstring calls it deliberate ("logged at WARNING since it silently changes
what is checked"), which makes it a design decision that has DECAYED INTO LOG
NOISE: nobody can act on a warning that is always true. That is the friction --
not the intent behind it.

THE THREE OPTIONS, AND WHY THIS LEAF PICKS ONE
(1) declare the pack in design/frob.strata -- correct but requires the
    design/frob.strata whole-file lease, i.e. blocked behind T-4598, and it is
    also arguably a model change the owner's grammar rethink touches;
(2) log ONCE per process (or per module identity) instead of per call;
(3) demote to DEBUG -- loses the signal entirely.
This leaf takes (2) so it stays scope-disjoint (src/frob/strata/_packs.py only,
no design/frob.strata, no T-4598 blocker) and preserves the signal for the first
occurrence. Option (1) remains open to the owner as part of story D's model
decisions; record that in the done-report if (2) is landed.

POSITIVE CONTROL (the test that fails today)
A test that calls load_design_ids twice in one process with caplog at WARNING
and asserts at most ONE require_analyzable warning record. It fails at HEAD:
one per call, 570 across 45 land logs. A second test must assert the FIRST
warning is still emitted -- otherwise this leaf silently becomes option (3).