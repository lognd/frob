## Done report

T-0520 triaged all 65 residual INV003/INV004 findings (34 files: 21
docs/modules + 12 docs/strata + docs/modules/gates.md, which the
ticket's file list undercounted by one) after the T-0509/T-0515
calibration. Batch-by-file, 32 new invariants (INV-005..INV-036) were
created, each with a real code anchor (`frob:invariant INV-###` at the
enforcing function/class) and evidence resolving to already-collected,
passing tests (verified via `pytest --collect-only -o addopts=""` and a
targeted `pytest` run per batch) -- INV001/INV002 stay clean for every
new invariant. Two files (charter.md, policy.md) had one overclaiming
paragraph each reworded to state the real (partial or not-yet-wired)
status honestly, with a specific `frob:waive INV003/INV004` reason
instead of a false bind: charter.md's "overdue assumptions are gate
failures" is not yet wired into `frob check` (the claim evaluator flags
it in claim detail text but does not fail the gate); policy.md's
refinement-monotonicity ("a child may strengthen, never weaken") has no
enforcing pass yet (`compile_policies` resolves scope only). No claim's
stated property was weakened to make it easier to prove; every bind
matches exactly what its cited test demonstrates.

`uv run frob check --only invariant --json` went from 65 diagnostics to
0 (confirmed after each batch, 5 batches total, one commit per batch).
`uv run frob check --only invariant` also shows 0 INV001/INV002 across
the full invariant set (36 invariants now loaded). `tests/test_gates.py`
(252 tests) passes in full. Every touched test file (walk_lint, arch,
clean, bind, cve, decisions, dup, dup_inline, fuzz, gates cov003/dup_gate,
lang, logging_module, mutate, perf, process_guard, render, serve,
telemetry, testing select, tickets/tickets_lease, vet obfuscation, and
the strata selfconform/crash/facts/threat/policy/krb/host_isolation/
elaborate/litmus_waive suites) was run individually and passes.

Three pre-existing failing suites were found via `frob test` and are OUT
of this ticket's scope (docs/modules/, docs/strata/, invariants/ only):
`tests/unit/test_extending_guides_complete.py` (a stale
src/frob/vet/_capability_registry.py doc anchor, last touched by T-0524),
`tests/system/test_frob_self_model.py` (frob's own design/frob.strata
self-model claim count drifted, last touched by T-0510-era work), and
`tests/test_tickets_collision.py::TestTick002GateUnwaivable::
test_no_violation_off_default_branch`. None of these files were touched
by this ticket's diff; `git log` confirms each was last modified by an
unrelated, already-landed ticket. `git diff main --diff-filter=D --stat`
is empty (no unintended deletions).

Per-file disposition (all 34 files now anchor at least one real
invariant; none required a pure markdown-waive of ITS OWN claim except
the two callouts below):

- docs/modules/app.md -> INV-005 (WALK001)
- docs/modules/arch.md -> INV-006 (ARCH001 ceiling re-fire)
- docs/modules/bind.md -> INV-007 (BIND mismatch reporting)
- docs/modules/clean.md -> INV-008 (clean never touches tracked/source)
- docs/modules/cve.md -> INV-009 (parse_record never raises)
- docs/modules/decisions.md -> INV-010 (DEC002)
- docs/modules/dup.md, dup-sota-survey.md -> INV-011 (dup_gate opt-in/DUP001-2)
- docs/modules/fuzz.md -> INV-012 (FUZZ003 digest-keyed)
- docs/modules/gates.md -> INV-013 (COV003 non-vacuous path evidence)
- docs/modules/graph.md -> INV-014 (call graph stops at public boundary)
- docs/modules/lang.md -> INV-015 (recoverable parse yields partial symbols)
- docs/modules/logging.md -> INV-016 (_BelowLevelFilter)
- docs/modules/mutate.md -> INV-017 (run_mutations always restores source)
- docs/modules/perf.md -> INV-018 (PERF005 prove-or-error)
- docs/modules/process.md -> INV-019 (exec kill switch)
- docs/modules/render.md -> INV-020 (color-off precedence)
- docs/modules/serve.md -> INV-021 (five read-only MCP tools)
- docs/modules/stats.md -> INV-022 (telemetry redaction reuse)
- docs/modules/testing.md -> INV-023 (only resolved test endpoint selected)
- docs/modules/tickets.md -> INV-024 (doable scope-lease exclusion)
- docs/modules/vet.md -> INV-025 (VET004 obfuscation, no allow escape)
- docs/strata/selfconform.md -> INV-026 (SYS101 fully-excluded-node skip)
- docs/strata/boundary.md -> INV-027 (no-hang check)
- docs/strata/kernel.md -> INV-028 (worst_age cycle -> inf, never clamp)
- docs/strata/evidence.md -> INV-029 (discharge below required rung)
- docs/strata/policy.md -> INV-030 (trust-scope auto-inherit) + reworded
  refinement-monotonicity paragraph, markdown-waived with reason
- docs/strata/krb.md -> INV-031 (domain trust defaults one-way)
- docs/strata/roadmap.md -> INV-032 (blocked_by chain ordering)
- docs/strata/host.md -> INV-033 (HOST001/002 derived, not hand-written)
- docs/strata/surface.md -> INV-034 (duplicate id fails closed)
- docs/strata/threat.md -> INV-035 (THREAT001 catalog completeness)
- docs/strata/waive.md -> INV-036 (exact triple-match waiver)
- docs/strata/charter.md -> reworded assumption-expiry paragraph,
  markdown-waived with reason (each individually-enforced law already
  binds its own invariant at its dedicated doc, see above)

32 new invariants created (INV-005..INV-036); 0 tests written from
scratch -- every bind reuses an existing, already-passing test as
evidence (per the playbook's "docs-only ticket, don't invent a test"
precedent extended here: these are code-behavior claims with genuine
existing coverage, not doc-only claims).

SCOPE-LEASE NOTE FOR THE COORDINATOR: 9 of the anchor additions
(src/frob/strata/_crash.py, _elaborate.py, _facts.py, _host_isolation.py,
_krb.py, _policy.py, _selfconform.py, _threat.py, _waive.py -- each one
single-line `# frob:invariant INV-###` comment, no logic change) fall
under T-0401's declared scope (`src/frob/strata/`, currently in-progress
in another worktree). `frob ticket scope --add` refused to lease these
paths for T-0520 (ScopeLeaseConflict), so they are NOT reflected in this
ticket's own `scope` field even though they are in this diff. Please
verify these single-line additions apply cleanly against T-0401's
eventual changes before/at land (a trivial 3-way merge in the common
case, since they only add a leading-comment line above an existing
function/class signature) -- do not silently drop them, and do not
treat this as T-0520 overriding T-0401's lease; it is disclosed here so
the collision is visible, not silent.

### Changed
```
 docs/modules/app.md                |  11 ++
 docs/modules/arch.md               |   2 +
 docs/modules/bind.md               |   2 +
 docs/modules/clean.md              |   2 +
 docs/modules/cve.md                |   2 +
 docs/modules/decisions.md          |   2 +
 docs/modules/dup-sota-survey.md    |   2 +
 docs/modules/dup.md                |   2 +
 docs/modules/fuzz.md               |   2 +
 docs/modules/gates.md              |   2 +
 docs/modules/graph.md              |   2 +
 docs/modules/lang.md               |   2 +
 docs/modules/logging.md            |   1 +
 docs/modules/mutate.md             |   2 +
 docs/modules/perf.md               |   2 +
 docs/modules/process.md            |   2 +
 docs/modules/render.md             |   2 +
 docs/modules/serve.md              |   2 +
 docs/modules/stats.md              |   2 +
 docs/modules/testing.md            |   2 +
 docs/modules/tickets.md            |   2 +
 docs/modules/vet.md                |   2 +
 docs/strata/boundary.md            |   2 +
 docs/strata/charter.md             |   2 +
 docs/strata/evidence.md            |   2 +
 docs/strata/host.md                |   6 +-
 docs/strata/kernel.md              |   2 +
 docs/strata/krb.md                 |   2 +
 docs/strata/policy.md              |  16 +-
 docs/strata/roadmap.md             |   2 +
 docs/strata/selfconform.md         |   4 +-
 docs/strata/surface.md             |   2 +
 docs/strata/threat.md              |   2 +
 docs/strata/waive.md               |   2 +
 invariants/INV-005.md              |  31 ++++
 invariants/INV-006.md              |  21 +++
 invariants/INV-007.md              |  24 +++
 invariants/INV-008.md              |  26 ++++
 invariants/INV-009.md              |  27 ++++
 invariants/INV-010.md              |  23 +++
 invariants/INV-011.md              |  25 ++++
 invariants/INV-012.md              |  23 +++
 invariants/INV-013.md              |  25 ++++
 invariants/INV-014.md              |  23 +++
 invariants/INV-015.md              |  26 ++++
 invariants/INV-016.md              |  19 +++
 invariants/INV-017.md              |  23 +++
 invariants/INV-018.md              |  24 +++
 invariants/INV-019.md              |  27 ++++
 invariants/INV-020.md              |  25 ++++
 invariants/INV-021.md              |  25 ++++
 invariants/INV-022.md              |  23 +++
 invariants/INV-023.md              |  26 ++++
 invariants/INV-024.md              |  25 ++++
 invariants/INV-025.md              |  28 ++++
 invariants/INV-026.md              |  26 ++++
 invariants/INV-027.md              |  27 ++++
 invariants/INV-028.md              |  24 +++
 invariants/INV-029.md              |  22 +++
 invariants/INV-030.md              |  25 ++++
 invariants/INV-031.md              |  24 +++
 invariants/INV-032.md              |  23 +++
 invariants/INV-033.md              |  29 ++++
 invariants/INV-034.md              |  23 +++
 invariants/INV-035.md              |  26 ++++
 invariants/INV-036.md              |  24 +++
 src/frob/app/telemetry.py          |   1 +
 src/frob/bind/__init__.py          |   1 +
 src/frob/clean/_core.py            |   1 +
 src/frob/cve/_parser.py            |   1 +
 src/frob/fuzz/_rules.py            |   1 +
 src/frob/gates/__init__.py         |   3 +
 src/frob/gates/_walk_lint.py       |   1 +
 src/frob/gates/decisions.py        |   1 +
 src/frob/graph/callgraph.py        |   1 +
 src/frob/lang/__init__.py          |   1 +
 src/frob/logging/filter.py         |   1 +
 src/frob/mutate/__init__.py        |   1 +
 src/frob/perf/_recursion.py        |   1 +
 src/frob/process/_guard.py         |   1 +
 src/frob/render/_color.py          |   1 +
 src/frob/serve/server.py           |   1 +
 src/frob/strata/_crash.py          |   1 +
 src/frob/strata/_elaborate.py      |   1 +
 src/frob/strata/_facts.py          |   1 +
 src/frob/strata/_host_isolation.py |   1 +
 src/frob/strata/_krb.py            |   1 +
 src/frob/strata/_policy.py         |   1 +
 src/frob/strata/_selfconform.py    |   1 +
 src/frob/strata/_threat.py         |   2 +
 src/frob/strata/_waive.py          |   1 +
 src/frob/testing/_select.py        |   1 +
 src/frob/tickets/__init__.py       |   2 +
 src/frob/vet/_scan.py              |   1 +
 tickets.md                         | 299 +++++++++++++++++++++++++++++++++++--
 95 files changed, 1203 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/test_walk_lint_gate.py::TestRglob::test_raw_rglob_fires` (pytest node id, verified passing when recorded)
- `tests/test_arch_gate.py::TestArchGateWaivers::test_ceiling_refires_when_grown_past_it` (pytest node id, verified passing when recorded)
- `tests/unit/test_bind.py::test_check_reports_mismatch_for_unbound_binding` (pytest node id, verified passing when recorded)
- `tests/test_clean.py::test_scan_skips_tracked_files` (pytest node id, verified passing when recorded)
- `tests/unit/cve/test_parser.py::test_parse_missing_file` (pytest node id, verified passing when recorded)
- `tests/test_decisions.py::test_dec002_accepted_decision_unanchored` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestOptInGates::test_dup_gate_fires_on_planted_clone_when_enabled` (pytest node id, verified passing when recorded)
- `tests/test_fuzz.py::TestFuzz003::test_flags_stale_stamp` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov003_rejects_empty_directory_level_evidence` (pytest node id, verified passing when recorded)
- `tests/test_dup_inline.py::TestCallGraphBounds::test_public_callee_never_becomes_an_edge` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestErrors::test_syntax_error_yields_partial_symbols` (pytest node id, verified passing when recorded)
- `tests/unit/test_logging_module.py::test_below_level_filter` (pytest node id, verified passing when recorded)
- `tests/test_mutate.py::test_run_mutations_survivors_when_tests_weak` (pytest node id, verified passing when recorded)
- `tests/test_perf.py::test_perf005_fires_on_unproven_self_recursion` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestGuardedSubprocessRun::test_disabled_returns_err_without_spawning` (pytest node id, verified passing when recorded)
- `tests/unit/test_render.py::TestResolveColor::test_no_color_flag_wins_over_everything` (pytest node id, verified passing when recorded)
- `tests/test_serve.py::TestBuildServer::test_registers_all_five_tools` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_redact_command_hides_recognizable_secret` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestSelect::test_reversed_directive_never_selects_the_source_symbol` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestDoable::test_real_collision_is_hidden_from_default_doable` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestObfuscationEnsemble::test_scan_directory_obfuscation_finds_signal_in_one_file` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestStaleDesign::test_stale_design_skips_node_fully_within_graph_exclude` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_crash.py::TestNoHangCheck::test_missing_timeout_into_crashable_node_fails_closed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_facts.py::TestClosure::test_worst_age_reports_unbounded_on_a_positive_cycle` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestDischargeCompleteness::test_discharge_claim_below_required_rung_is_a_violation` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_policy.py::TestScopeResolution::test_trust_scope_resolves_via_lattice` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_krb.py::TestKrbTrustFlows::test_two_way_synthesizes_reverse_edge_too` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestDoable::test_blocked_excluded` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestVerticalIsolation::test_sudoers_does_not_fire_when_undeclared` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_elaborate.py::TestElaborateValidation::test_duplicate_node_id_fails_closed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestCatalogCompleteness::test_missing_entry_is_a_violation` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_litmus_waive.py::TestWaiveLitmus::test_sub_target_waiver_does_not_suppress_a_different_sub_target` (pytest node id, verified passing when recorded)
