---
id: T-1018
title: 'PERF012 dup-spawn advisory calibration: 20 -> 1777 findings after T-0922 substrate
  expansion'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: high
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/perf/_dup_spawn.py
- src/frob/perf/_effect_summaries.py
- src/frob/perf/_rules.py
- tests/test_perf.py
- docs/modules/perf.md
- tests/unit/perf/test_dup_spawn.py
- tests/unit/perf/test_effect_summaries.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/perf.md
  reason: 'T-1018: added regression tests under tests/unit/perf/ (mirroring the existing
    PERF012/EffectGraph test module layout) and updated docs/modules/perf.md''s PERF012/EffectGraph
    sections with the calibration write-up'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/unit/perf/test_dup_spawn.py
  reason: 'T-1018: added regression tests under tests/unit/perf/ (mirroring the existing
    PERF012/EffectGraph test module layout) and updated docs/modules/perf.md''s PERF012/EffectGraph
    sections with the calibration write-up'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/unit/perf/test_effect_summaries.py
  reason: 'T-1018: added regression tests under tests/unit/perf/ (mirroring the existing
    PERF012/EffectGraph test module layout) and updated docs/modules/perf.md''s PERF012/EffectGraph
    sections with the calibration write-up'
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/perf/test_dup_spawn.py::TestPerf012CalibrationT1018::test_before_after_state_check_with_mutation_between_is_not_flagged
- tests/unit/perf/test_dup_spawn.py::TestPerf012CalibrationT1018::test_adjacent_true_positive_still_fires_after_interleaving_fix
- tests/unit/perf/test_dup_spawn.py::TestPerf012CalibrationT1018::test_splat_forwarding_wrapper_called_with_different_args_is_not_flagged
- tests/unit/perf/test_effect_summaries.py::TestSplatArgumentDegradesToUnknown::test_splat_argument_nested_in_a_literal_yields_an_unknown_member
- tests/unit/perf/test_effect_summaries.py::TestSplatArgumentDegradesToUnknown::test_plain_named_parameter_forward_is_not_treated_as_a_splat
designated_repro_test: null
acceptance:
- text: GIVEN a full frob check run WHEN PERF012 fires THEN every remaining finding
    is a true independently-reachable duplicate spawn (spot-check 10) and the total
    is accounted (fixed, waived-with-grounds, or ticketed)
  evidence:
  - tests/unit/perf/test_dup_spawn.py::TestPerf012CalibrationT1018::test_before_after_state_check_with_mutation_between_is_not_flagged
  - tests/unit/perf/test_dup_spawn.py::TestPerf012CalibrationT1018::test_adjacent_true_positive_still_fires_after_interleaving_fix
threat: null
component: null
---
Full-run PERF012 count is 1777 warnings; at T-0919 land it reported 20 repo findings. The T-0922 EffectGraph substrate (explicit Unknown) most likely broadened reach into massive over-fire. Triage the findings into clusters, identify false-positive classes (e.g. Unknown-summary conflation, same-shape-but-different-target spawns), fix the detector for each FP class with before/after counts, then burn down or grounds-waive the honest remainder. Both-layers rule applies to any rule-shape change.