---
id: T-0922
title: 'perf: shared interprocedural effect-summary substrate for all PERF rules (sub-call
  tracking)'
state: done
kind: feature
origin: human
created: '2026-07-26'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/perf/**
- tests/unit/perf/**
- docs/modules/perf.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect::test_loop_invariant_spawn_call_three_hops_deep_is_flagged
- tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_three_hop_duplicate_split_across_sibling_callees_is_flagged
- tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_two_helpers_spawning_identical_subprocess_is_flagged
- tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_multi_hop_duplicate_via_different_intermediate_callees_is_flagged
- tests/unit/perf/test_effect_summaries.py::TestEffectGraphSummaryUnknownDegradation::test_ambiguous_cross_file_callee_yields_an_explicit_unknown_member
- tests/unit/perf/test_effect_summaries.py::TestUnknownIdentityEquality::test_two_unknowns_with_the_same_reason_text_are_not_equal
- tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_unresolvable_dynamic_dispatch_callee_never_manufactures_a_duplicate
- tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect::test_unresolvable_callee_does_not_crash_and_does_not_fire
designated_repro_test: null
acceptance:
- text: given an expensive effect (spawn/fs-walk/net/heavy-parse) occurring only inside
    a callee 2+ hops below the analyzed function, when any PERF rule that keys on
    that effect class analyzes the caller, then the effect is attributed to the caller's
    call path and the rule fires identically to a direct occurrence
  evidence:
  - tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect::test_loop_invariant_spawn_call_three_hops_deep_is_flagged
  - tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_three_hop_duplicate_split_across_sibling_callees_is_flagged
- text: given duplicate identical spawns split across two sibling callees reached
    from one call path, when PERF012-class duplicate-spawn analysis runs, then the
    duplicate is detected across the sub-call boundary with argv-equivalence facts
    propagated through the summaries
  evidence:
  - tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_two_helpers_spawning_identical_subprocess_is_flagged
  - tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_multi_hop_duplicate_via_different_intermediate_callees_is_flagged
  - tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_three_hop_duplicate_split_across_sibling_callees_is_flagged
- text: given a call the resolver cannot bind (dynamic dispatch, external boundary),
    when summaries are propagated, then the effect set degrades to an explicit Unknown
    rather than silently empty, and rules document their Unknown policy
  evidence:
  - tests/unit/perf/test_effect_summaries.py::TestEffectGraphSummaryUnknownDegradation::test_ambiguous_cross_file_callee_yields_an_explicit_unknown_member
  - tests/unit/perf/test_effect_summaries.py::TestUnknownIdentityEquality::test_two_unknowns_with_the_same_reason_text_are_not_equal
  - tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_unresolvable_dynamic_dispatch_callee_never_manufactures_a_duplicate
  - tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect::test_unresolvable_callee_does_not_crash_and_does_not_fire
threat: null
component: null
---
User directive 2026-07-27: expensive-operation detection (subprocess.run is an EXAMPLE, not the whole list) must track occurrences in sub-function calls -- e.g. PERF012 repeated-duplicate-spawn must fire when the duplicates happen inside callees or are split across callees. Promote PERF008's _EffectGraph (src/frob/perf/_loop_effects.py, name-based whole-project callee propagation) into a shared per-function effect-summary substrate: function -> multiset of summarized effects with argument-invariance/argv facts, transitively propagated, explicit Unknown on unresolvable bindings (reuse the T-0659 binding-resolver conventions and the T-0745 summary-fixpoint precedent rather than inventing a third engine). All existing PERF rules (PERF008 loop-invariant effects, PERF012 duplicate spawns, future rules) consume the same summaries. Structural twin: the .strata perf obligations should consume the same facts where applicable (per the both-layers rule from T-0919). The user wants an incredibly sophisticated checker: depth over minimalism, with multi-hop true-positive tests and call-site-varying false-positive guards.