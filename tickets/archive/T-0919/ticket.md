---
id: T-0919
title: done-report's internal check_gates/check_gate_findings spawns are too slow
  for CLI foreground use (T-0887 follow-up)
state: done
kind: bug
origin: human
created: '2026-07-26'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/perf/**
- src/frob/strata/**
- tests/unit/perf/**
- tests/unit/strata/**
- docs/modules/perf.md
- tests/unit/test_ticket_runner_gate_findings.py
- docs/strata/reliability.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/perf/**
  reason: 'Repo owner directive (recorded on T-0919): anything found while root-causing

    the done-report spawn slowness must also be encoded as a lint in BOTH the

    structural (.strata) and code (perf) layers, and a follow-up user directive

    required the perf detector to be genuinely interprocedural (extending

    frob.perf._loop_effects''s shared EffectGraph substrate). Widening scope to

    cover src/frob/perf/**, src/frob/strata/**, tests/unit/perf/**,

    tests/unit/strata/**, docs/modules/perf.md, and the ticket_runner test file

    touched by the shared-spawn fix and its coverage annotations.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: src/frob/strata/**
  reason: 'Repo owner directive (recorded on T-0919): anything found while root-causing

    the done-report spawn slowness must also be encoded as a lint in BOTH the

    structural (.strata) and code (perf) layers, and a follow-up user directive

    required the perf detector to be genuinely interprocedural (extending

    frob.perf._loop_effects''s shared EffectGraph substrate). Widening scope to

    cover src/frob/perf/**, src/frob/strata/**, tests/unit/perf/**,

    tests/unit/strata/**, docs/modules/perf.md, and the ticket_runner test file

    touched by the shared-spawn fix and its coverage annotations.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: tests/unit/perf/**
  reason: 'Repo owner directive (recorded on T-0919): anything found while root-causing

    the done-report spawn slowness must also be encoded as a lint in BOTH the

    structural (.strata) and code (perf) layers, and a follow-up user directive

    required the perf detector to be genuinely interprocedural (extending

    frob.perf._loop_effects''s shared EffectGraph substrate). Widening scope to

    cover src/frob/perf/**, src/frob/strata/**, tests/unit/perf/**,

    tests/unit/strata/**, docs/modules/perf.md, and the ticket_runner test file

    touched by the shared-spawn fix and its coverage annotations.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: tests/unit/strata/**
  reason: 'Repo owner directive (recorded on T-0919): anything found while root-causing

    the done-report spawn slowness must also be encoded as a lint in BOTH the

    structural (.strata) and code (perf) layers, and a follow-up user directive

    required the perf detector to be genuinely interprocedural (extending

    frob.perf._loop_effects''s shared EffectGraph substrate). Widening scope to

    cover src/frob/perf/**, src/frob/strata/**, tests/unit/perf/**,

    tests/unit/strata/**, docs/modules/perf.md, and the ticket_runner test file

    touched by the shared-spawn fix and its coverage annotations.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: docs/modules/perf.md
  reason: 'Repo owner directive (recorded on T-0919): anything found while root-causing

    the done-report spawn slowness must also be encoded as a lint in BOTH the

    structural (.strata) and code (perf) layers, and a follow-up user directive

    required the perf detector to be genuinely interprocedural (extending

    frob.perf._loop_effects''s shared EffectGraph substrate). Widening scope to

    cover src/frob/perf/**, src/frob/strata/**, tests/unit/perf/**,

    tests/unit/strata/**, docs/modules/perf.md, and the ticket_runner test file

    touched by the shared-spawn fix and its coverage annotations.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: tests/unit/test_ticket_runner_gate_findings.py
  reason: 'Repo owner directive (recorded on T-0919): anything found while root-causing

    the done-report spawn slowness must also be encoded as a lint in BOTH the

    structural (.strata) and code (perf) layers, and a follow-up user directive

    required the perf detector to be genuinely interprocedural (extending

    frob.perf._loop_effects''s shared EffectGraph substrate). Widening scope to

    cover src/frob/perf/**, src/frob/strata/**, tests/unit/perf/**,

    tests/unit/strata/**, docs/modules/perf.md, and the ticket_runner test file

    touched by the shared-spawn fix and its coverage annotations.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: docs/strata/reliability.md
  reason: REL31x obligation doc section lives here, same directive-authorized widening
    as the rest of this ticket's structural-layer scope
  actor: logan
  at: '2026-07-26'
evidence:
- tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn::test_second_call_does_not_spawn_again
- tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn::test_check_gates_summary_fn_and_check_gate_findings_fn_share_one_spawn
- tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn::test_default_spawn_none_keeps_each_closure_independent
- tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_two_helpers_spawning_identical_subprocess_is_flagged
- tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_two_helpers_spawning_different_subprocess_args_is_not_flagged
- tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_single_helper_call_is_not_flagged
- tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_multi_hop_duplicate_via_different_intermediate_callees_is_flagged
- tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_call_site_varying_argument_is_not_flagged
- tests/unit/strata/test_interactive_cost.py::TestMissingBoundedCost::test_interactive_node_without_bounded_cost_fires
- tests/unit/strata/test_interactive_cost.py::TestMissingBoundedCost::test_discharged_and_non_interactive_nodes_clean
- tests/unit/strata/test_interactive_cost.py::TestMissingBoundedCost::test_waiver_discharges_finding
- tests/unit/strata/test_interactive_cost.py::TestUnprovenBoundedCost::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_interactive_cost.py::TestUnprovenBoundedCost::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_interactive_cost.py::TestUnprovenBoundedCost::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
- tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn::test_spawn_kwargs_capture_output_text_and_no_check
designated_repro_test: null
threat: null
component: null
---
## Description

T-0887 fixed the two acceptance-criteria-facing hangs on `frob ticket
done-report --base-ref`: an unresolvable ref now fails fast
(`base_ref_resolvable`), and the read-only `check_gates`/
`check_gate_findings` claims capture no longer holds `ledger_lock` for
its duration (fixing the concurrent-lock-contention hang class).

What T-0887 deliberately did NOT fix, disclosed in its Done report: the
CLI command `frob ticket done-report <id>` itself still spawns TWO
SEPARATE full `python -m frob check --ticket <id>` subprocesses
serially (`_check_gates_summary_fn`/`_check_gate_findings_fn` in
`src/frob/app/ticket_runner.py`), each with a 600s timeout. On this
repo's own tree a full (all-stage-group) `frob check` run measures well
past the ~120s foreground cap the agent playbook documents (section
3b) -- so `frob ticket done-report` itself remains effectively
unusable from an agent's own foreground shell (confirmed empirically
while closing T-0887: a `timeout 100` wrapper around `frob ticket
done-report T-0887 ...` was killed before either check spawn finished).

## Plan (not yet built, left for this ticket)

Investigate: (a) deduplicating the two full-check spawns into one
shared subprocess run (already flagged as a known cost tradeoff in
`_check_gate_findings_fn`'s own docstring); (b) whether `--only` stage
selection (the same chunking the playbook already recommends for
interactive agents) is safe to apply to these internal spawns without
weakening the claim's coverage; (c) whether a shorter, configurable
timeout with a clear "gate state unmeasured" fallback (the existing
`None` path `_check_gates_summary_fn` already has for a refused/
unparsable spawn) is preferable to unconditionally waiting up to
1200s combined.