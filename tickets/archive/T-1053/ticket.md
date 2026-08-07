---
id: T-1053
title: 'perf detectors: kill three recurring FP classes -- bare-method-name coincidence
  (str.count/.index on the loop''s own element), receiver conflation, and lru_cache
  blindness'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/perf/_loop_effects.py
- src/frob/perf/_dup_spawn.py
- tests/test_perf.py
- docs/modules/perf.md
- src/frob/perf/_rules.py
- src/frob/perf/_effect_summaries.py
- tests/unit/perf/test_loop_effects.py
- tests/unit/perf/test_dup_spawn.py
- tests/unit/perf/test_effect_summaries.py
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/perf/_rules.py
  reason: 're-applying T-1053''s earlier scope widening after the section-10b tickets.md
    restore-from-main step dropped it (only committed on this worktree branch, not
    on main); same reasons as the original --add calls: PERF002 lives in _rules.py
    (hard prereq for acceptance criterion 0), _effect_summaries.py is the shared substrate
    both in-scope rules call private helpers on, the two rules'' unit-test files needed
    extending, gates/__init__.py carries the one confirmed-retirable lru_cache PERF008
    waiver'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/perf/_effect_summaries.py
  reason: 're-applying T-1053''s earlier scope widening after the section-10b tickets.md
    restore-from-main step dropped it (only committed on this worktree branch, not
    on main); same reasons as the original --add calls: PERF002 lives in _rules.py
    (hard prereq for acceptance criterion 0), _effect_summaries.py is the shared substrate
    both in-scope rules call private helpers on, the two rules'' unit-test files needed
    extending, gates/__init__.py carries the one confirmed-retirable lru_cache PERF008
    waiver'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/perf/test_loop_effects.py
  reason: 're-applying T-1053''s earlier scope widening after the section-10b tickets.md
    restore-from-main step dropped it (only committed on this worktree branch, not
    on main); same reasons as the original --add calls: PERF002 lives in _rules.py
    (hard prereq for acceptance criterion 0), _effect_summaries.py is the shared substrate
    both in-scope rules call private helpers on, the two rules'' unit-test files needed
    extending, gates/__init__.py carries the one confirmed-retirable lru_cache PERF008
    waiver'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/perf/test_dup_spawn.py
  reason: 're-applying T-1053''s earlier scope widening after the section-10b tickets.md
    restore-from-main step dropped it (only committed on this worktree branch, not
    on main); same reasons as the original --add calls: PERF002 lives in _rules.py
    (hard prereq for acceptance criterion 0), _effect_summaries.py is the shared substrate
    both in-scope rules call private helpers on, the two rules'' unit-test files needed
    extending, gates/__init__.py carries the one confirmed-retirable lru_cache PERF008
    waiver'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/perf/test_effect_summaries.py
  reason: 're-applying T-1053''s earlier scope widening after the section-10b tickets.md
    restore-from-main step dropped it (only committed on this worktree branch, not
    on main); same reasons as the original --add calls: PERF002 lives in _rules.py
    (hard prereq for acceptance criterion 0), _effect_summaries.py is the shared substrate
    both in-scope rules call private helpers on, the two rules'' unit-test files needed
    extending, gates/__init__.py carries the one confirmed-retirable lru_cache PERF008
    waiver'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 're-applying T-1053''s earlier scope widening after the section-10b tickets.md
    restore-from-main step dropped it (only committed on this worktree branch, not
    on main); same reasons as the original --add calls: PERF002 lives in _rules.py
    (hard prereq for acceptance criterion 0), _effect_summaries.py is the shared substrate
    both in-scope rules call private helpers on, the two rules'' unit-test files needed
    extending, gates/__init__.py carries the one confirmed-retirable lru_cache PERF008
    waiver'
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_perf.py::test_perf002_does_not_fire_on_the_loops_own_per_iteration_element
- tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect::test_loop_invariant_call_to_lru_cached_helper_is_not_flagged
- tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect::test_receiver_conflation_binds_only_to_the_matching_receivers_class
- tests/unit/perf/test_dup_spawn.py::TestPerf012T1053FalsePositiveClasses::test_two_call_sites_to_an_lru_cached_helper_are_not_flagged
- tests/unit/perf/test_dup_spawn.py::TestPerf012T1053FalsePositiveClasses::test_receiver_conflation_binds_only_to_the_matching_receivers_class
- tests/unit/perf/test_effect_summaries.py::TestMemoizedCalleeDetection::test_lru_cache_decorated_symbol_is_memoized
- tests/unit/perf/test_effect_summaries.py::TestMemoizedCalleeDetection::test_undecorated_symbol_is_not_memoized
- tests/unit/perf/test_effect_summaries.py::TestMemoizedCalleeDetection::test_bare_cache_named_parameter_is_not_mistaken_for_a_decorator
- tests/unit/perf/test_effect_summaries.py::TestMemoizedCalleeDetection::test_functools_dotted_lru_cache_decorator_is_memoized
designated_repro_test: null
acceptance:
- text: 'given a loop ''for line in lines: line.count(x)'', when PERF002 evaluates,
    then no finding fires because the receiver is the loop''s own per-iteration element,
    not a repeated collection scan'
  evidence:
  - tests/test_perf.py::test_perf002_does_not_fire_on_the_loops_own_per_iteration_element
- text: given a loop calling an lru_cache-decorated function with loop-invariant args,
    when PERF008 evaluates, then the finding is suppressed or downgraded because the
    call is memoized
  evidence:
  - tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect::test_loop_invariant_call_to_lru_cached_helper_is_not_flagged
- text: given two different receivers sharing a method short name inside a loop, when
    any PERF rule matches by method name, then the finding binds only to the receiver
    whose type/effect actually matches the rule
  evidence:
  - tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect::test_receiver_conflation_binds_only_to_the_matching_receivers_class
threat: null
component: null
---
Three FP classes observed across the 2026-07 drive: (1) bare-method-name coincidence -- PERF002 flagged str.count on the loop's own per-iteration line in src/frob/arch/_cpp_mayraise.py (waived e69fd22d); same class produced the original PERF008 FP body lost twice to draft-renumber clobbers (see commits c00a8c1a / d9e51579 for the full catalogue: bare-method-name coincidence, receiver conflation, lru_cache blindness). (2) receiver conflation -- a rule keyed on method name attributes effects of one receiver's method to a different receiver. (3) lru_cache blindness -- repeated calls to a memoized function are flagged as repeated work. Each class should get a litmus fixture that locks current behavior before the fix, per the T-0666 pattern.