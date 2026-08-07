---
id: T-0747
title: 'cleanup obligations: release-postdominates-acquisition on all exits incl.
  exceptional, escape transfer, per-protocol policy'
state: done
kind: security
origin: human
created: '2026-07-22'
priority: high
blocked_by:
- T-0745
- T-0686
parent: T-0739
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- src/frob/gates/**
- tests/test_gates.py
- docs/modules/gates.md
- docs/modules/graph.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: 'Every new public symbol PROTO005 introduces needs a frob:doc edge

    resolving to a real anchor (COV001), and the DSL-level "this is the

    surface only, verification is T-0747" note in docs/modules/graph.md''s

    resource-tracking section needed updating now that the verifier exists --

    same T-0745 precedent (docs/modules/graph.md added to that ticket''s scope

    for the identical reason).

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: docs/modules/graph.md
  reason: 'Every new public symbol PROTO005 introduces needs a frob:doc edge

    resolving to a real anchor (COV001), and the DSL-level "this is the

    surface only, verification is T-0747" note in docs/modules/graph.md''s

    resource-tracking section needed updating now that the verifier exists --

    same T-0745 precedent (docs/modules/graph.md added to that ticket''s scope

    for the identical reason).

    '
  actor: logan
  at: '2026-07-26'
evidence:
- tests/test_gates.py::TestCleanupObligationGate::test_early_return_before_release_call_is_an_error
- tests/test_gates.py::TestCleanupObligationGate::test_release_before_return_is_not_flagged
- tests/test_gates.py::TestCleanupObligationGate::test_escape_transfer_discharges_the_obligation
- tests/test_gates.py::TestCleanupObligationGate::test_self_contained_acquire_and_release_is_trusted
- tests/test_gates.py::TestCleanupObligationGate::test_python_with_block_discharges_the_acquisition
- tests/test_gates.py::TestCleanupObligationGate::test_process_exit_ok_policy_discharges_a_terminator_guarded_return
- tests/test_gates.py::TestCleanupObligationGate::test_exceptional_exit_with_no_release_anywhere_is_an_error
- tests/test_gates.py::TestCleanupObligationGate::test_deinit_never_called_for_cleanup_always_protocol_is_an_error
- tests/test_gates.py::TestCleanupObligationGate::test_deinit_reachable_for_cleanup_always_protocol_is_not_flagged
designated_repro_test: null
acceptance:
- text: GIVEN a C fixture acquiring a resource with an early-error return skipping
    cleanup WHEN the gate runs THEN an ERROR names the leaking path; GIVEN the Python
    equivalent inside a with-block THEN a recorded context-manager discharge; GIVEN
    cleanup=process-exit-ok THEN termination paths discharge silently by declared
    policy only
  evidence:
  - tests/test_gates.py::TestCleanupObligationGate::test_early_return_before_release_call_is_an_error
  - tests/test_gates.py::TestCleanupObligationGate::test_python_with_block_discharges_the_acquisition
  - tests/test_gates.py::TestCleanupObligationGate::test_process_exit_ok_policy_discharges_a_terminator_guarded_return
threat: null
component: null
---
Child 4 of T-0739. Cleanup obligations: (a) intraprocedural -- every acquisition (transition into a resource-held state) must be postdominated by its release on ALL exits, using T-0686 may-raise sets for the exceptional edges (blocked_by T-0686), UNLESS the resource escapes (returned/stored) -- escape transfers the obligation to the receiver via the summary (T-0745); (b) per-protocol cleanup policy: cleanup = always | on-error | process-exit-ok, declared in the protocol (T-0744), default on-error; the *_deinit-never-called case = a protocol with cleanup=always whose deinit is unreachable from entrypoint terminating paths = ERROR. NO-FAIL-SILENT: a path the analysis cannot classify (poisoned/Unknown) is an ERROR at the acquisition site; escapes into containers/globals the summary cannot track are reported as obligation-escaped-untracked findings (waivable), never dropped.