---
id: T-0973
title: 'Burn-down: SEC110 to zero unwaived, then promote to ERROR (16 findings)'
state: done
kind: security
origin: auditor
created: '2026-07-27'
priority: high
parent: T-0969
tier: ticket
sprint: null
scope:
- src/frob/app/check_runner.py
- src/frob/app/stats_runner.py
- src/frob/app/telemetry.py
- src/frob/perf/_harness.py
- src/frob/process/_guard.py
- src/frob/render/_color.py
- src/frob/testing/_runners.py
- src/frob/tickets/_land.py
- src/frob/tickets/_worktree_guard.py
- src/frob/vet/_source.py
- tests/test_testing.py
- tests/test_ticket_land.py
- tests/test_tickets_mutation_evidence.py
- frob.toml
- src/frob/gates/__init__.py
- tests/test_gates.py
- docs/modules/gates.md
- docs/modules/perf.md
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: ticket's own plan names 3 of the 16 SEC110 findings in gates/__init__.py;
    scope glob list omitted this file by oversight
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/test_gates.py
  reason: add SEC110 severity-promotion before-fails/after-passes fixture test proving
    the WARN->ERROR flip actually gates, per T-0756 acceptance policy
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/gates.md
  reason: AFFECT001 requires touching the affects()-closure docs for the 3 functions
    whose SEC110 frob:waive comment changed their digest (_rel001_bump_suppressed_under_agent,
    perf._harness.main, _worktree_guard.enforce_worktree_lease)
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/perf.md
  reason: AFFECT001 requires touching the affects()-closure docs for the 3 functions
    whose SEC110 frob:waive comment changed their digest (_rel001_bump_suppressed_under_agent,
    perf._harness.main, _worktree_guard.enforce_worktree_lease)
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/tickets.md
  reason: AFFECT001 requires touching the affects()-closure docs for the 3 functions
    whose SEC110 frob:waive comment changed their digest (_rel001_bump_suppressed_under_agent,
    perf._harness.main, _worktree_guard.enforce_worktree_lease)
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_gates.py::TestSeverityOverrides::test_sec110_promoted_to_error_gates_a_real_repo_toml
- tests/test_ticket_land.py::TestLandInternalEnvThroughHook::test_land_internal_git_env_restores_prior_value
- tests/test_worktree_guard.py::TestEnforceWorktreeLease::test_matching_worktree_passes
- tests/unit/perf/test_harness_sampling.py::TestHarnessSerialPoolsDecision::test_env_zero_skips_serial_pools
- tests/unit/perf/test_harness_sampling.py::TestHarnessSampling::test_sampled_run_logs_hotgraph_summary
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_bare_check_refuses_under_frob_agent
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_allow_full_check_override_bypasses_refusal
- tests/test_tickets_mutation_evidence.py::TestEvidenceTestIds::test_filters_non_node_id_entries
designated_repro_test: null
threat: null
component: null
---
gates-quality audit (T-0399) finding 1/10: SEC110 is WARN-only and never
blocks `frob check`. Live measured count on main (chunked
`gates-security`, 2026-07-27): 16 unwaived SEC110 findings (10 already
carry a reasoned frob:waive) -- small enough to close out fully, unlike
the PERF/PII/ARCH families. Named sites (from the 2026-07-27 measurement):
src/frob/app/check_runner.py:857,859; src/frob/app/stats_runner.py:27;
src/frob/app/telemetry.py:47; src/frob/gates/__init__.py:8995,10439,10602
(or nearby -- line numbers drift with edits, re-grep at pickup);
src/frob/perf/_harness.py:110,114; src/frob/process/_guard.py:67;
src/frob/render/_color.py:57; src/frob/testing/_runners.py:390,400;
src/frob/tickets/_land.py:107,108,115; src/frob/tickets/_worktree_guard.py:68;
src/frob/vet/_source.py:35; tests/test_testing.py:901-903;
tests/test_ticket_land.py:3825,3828,3831,3832;
tests/test_tickets_mutation_evidence.py:305.

Plan: add a reasoned `frob:waive SEC110 reason="..."` to each site that is
a genuine non-secret flag/cache-path/behavior toggle (most of the list
above, by inspection), or map any real secret-shaped read to a declared
std.secrets node (T-0082) if one turns up. Owner-gate: SEC110 in
[gates.severity] -- flip to "error" once this list is at zero unwaived.