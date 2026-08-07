---
id: T-0775
title: 'perf: loop-invariant effectful call detector (spawn/fs-walk callee in a loop
  with loop-invariant args)'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: high
blocked_by:
- T-0632
parent: null
tier: ticket
sprint: null
scope:
- src/frob/perf/**
- src/frob/arch/**
- tests/unit/perf/
- docs/modules/perf.md
- tests/test_perf_loop_invariant_effect_lock.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/perf.md
  reason: 'New public symbol (loop_invariant_effect_violations, PERF008) requires
    a

    frob:doc anchor per COV001; docs/modules/perf.md is the existing home for

    every other PERF rule (PERF001-007) and this ticket''s own acceptance

    criteria describe user-facing detector behavior that belongs in the same

    rule table, not a separate doc page.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: tests/test_perf_loop_invariant_effect_lock.py
  reason: 'tests/test_perf_loop_invariant_effect_lock.py is a pre-existing, strict

    xfail lock this ticket''s own landing is designed to trip: its docstring

    says "When T-0775 lands ... the unexpected pass hard-errors (strict),

    forcing the marker''s removal -- at which point ALSO tighten the assertion

    to the new rule id". PERF008 now fires on this exact fixture, so the

    xfail marker must be removed and the assertion pinned to PERF008 or the

    suite hard-fails; this is required landing work for T-0775, not a

    different ticket''s scope.

    '
  actor: logan
  at: '2026-07-26'
evidence:
- tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect::test_fs_walk_direct_call_in_loop_is_flagged
- tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect::test_loop_invariant_spawn_call_two_hops_deep_is_flagged
- tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect::test_ticket_row_rev_parse_shape_fires_on_real_repo_history_fixture
- tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect::test_loop_varying_argument_is_not_flagged
- tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect::test_no_effectful_call_in_loop_is_not_flagged
- tests/test_perf_loop_invariant_effect_lock.py::test_loop_invariant_spawning_callee_in_loop_is_flagged
designated_repro_test: null
acceptance:
- text: GIVEN a fixture where a loop body calls a function that transitively spawns
    a process with arguments invariant across iterations WHEN frob check runs THEN
    a prove-or-justify finding fires naming the call site, the effectful callee, and
    the invariant args; GIVEN the same call with a loop-varying argument THEN no finding;
    GIVEN the pre-T-0773 read_all_leases-per-ticket-row shape THEN the finding fires
    on the real repo history fixture
  evidence:
  - tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect::test_ticket_row_rev_parse_shape_fires_on_real_repo_history_fixture
threat: null
component: null
---
Motivated by the 2026-07-22 rev-parse incident (T-0773): frob ticket list spawned git rev-parse --git-common-dir dozens of times because the loop (ticket rows) and the effect (subprocess spawn 3 calls deep) live in different modules -- no per-function syntactic PERF heuristic can see it. The ingredients already exist: vet capability observation knows which functions transitively proc.spawn/fs-walk; the obligation graph has the call graph; T-0632 adds per-argument call detail needed for the loop-invariance test. Detector: for each loop (incl. comprehensions and per-item pipeline stages), for each reachable effectful callee whose observed effect is spawn/fs-walk, if every argument at the call site is loop-invariant, fire a prove-or-justify finding (hoist, memoize, or frob:waive with a freshness justification -- re-reading mutable state can be deliberate under concurrency, so this is warn-tier with an unwaivable-style justification requirement, not a silent error). Keep recall honest: undecidable invariance leans toward firing per the repo philosophy.