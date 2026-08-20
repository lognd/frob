---
id: T-2732
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-2723):
  137 new (rule, file) identit(ies), 1 finding(s) (ARCH001, ARCH102, ARCH103, E501)'
state: done
kind: bug
origin: agent
created: '2026-08-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/fleet_status.py
- src/frob/_cli_parsers/_ticket/_closeout.py
- src/frob/app/_check_chunking.py
- src/frob/app/_daemon_proxy.py
- src/frob/app/app.py
- src/frob/app/bind_runner.py
- src/frob/app/cycle_runner.py
- src/frob/app/graph_runner.py
- src/frob/app/parse_runner.py
- src/frob/app/perf_runner.py
- src/frob/app/scaffold_runner.py
- src/frob/app/stats_runner.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/arch/_concurrency.py
- src/frob/arch/_cpp_mayraise.py
- src/frob/arch/_exceptions.py
- src/frob/arch/_fallibility.py
- src/frob/arch/_ffi.py
- src/frob/arch/_kotlin.py
- src/frob/arch/_ocp.py
- src/frob/arch/_patterns.py
- src/frob/arch/_python.py
- src/frob/arch/_rust.py
- src/frob/arch/_shared_state_race.py
- src/frob/arch/_smells.py
- src/frob/arch/_solid.py
- src/frob/arch/_typedesign.py
- src/frob/arch/_typescript.py
- src/frob/check/_ts.py
- src/frob/cycle/graph.py
- src/frob/deploy/_generate_common.py
- src/frob/dup/_pipeline/_normalize.py
- src/frob/dup/_template.py
- src/frob/fuzz/_signatures.py
- src/frob/gates/_coverage.py
- src/frob/gates/_dead_symbols.py
- src/frob/gates/_debt_deprecated.py
- src/frob/gates/_deprecated_baseline.py
- src/frob/gates/_design_invariants.py
- src/frob/gates/_docblocks.py
- src/frob/gates/_docblocks_refs.py
- src/frob/gates/_ffi_boundary.py
- src/frob/gates/_lang_conformance.py
- src/frob/gates/_registry_exhaustiveness.py
- src/frob/gates/_rule_id_scan.py
- src/frob/gates/_waive.py
- src/frob/gates/_waive_comments.py
- src/frob/gitio.py
- src/frob/graph/__init__.py
- src/frob/graph/affects.py
- src/frob/graph/callgraph.py
- src/frob/graph/summary.py
- src/frob/lang/__init__.py
- src/frob/lang/_common.py
- src/frob/lang/_support.py
- src/frob/natives/_build.py
- src/frob/perf/_advisories.py
- src/frob/perf/_dup_spawn.py
- src/frob/perf/_hotgraph.py
- src/frob/perf/_hotpath_smells.py
- src/frob/perf/_loop_effects.py
- src/frob/perf/_sampler.py
- src/frob/perf/_sketch_store.py
- src/frob/refactor/_scan.py
- src/frob/render/_elements.py
- src/frob/serve/_events.py
- src/frob/serve/_socketd.py
- src/frob/stats/_sketch.py
- src/frob/strata/_contention.py
- src/frob/strata/_design_load.py
- src/frob/strata/_distributed_txn.py
- src/frob/strata/_elaborate.py
- src/frob/strata/_export.py
- src/frob/strata/_facts.py
- src/frob/strata/_host_isolation.py
- src/frob/strata/_infra.py
- src/frob/strata/_lint.py
- src/frob/strata/_models.py
- src/frob/strata/_native_staleness.py
- src/frob/strata/_pii.py
- src/frob/strata/_selfconform.py
- src/frob/strata/_shared_state.py
- src/frob/strata/_ssot.py
- src/frob/strata/_starvation.py
- src/frob/strata/_sync_may.py
- src/frob/strata/_sysdoc.py
- src/frob/strata/_threat.py
- src/frob/strata/_txn.py
- src/frob/testing/_collect_cpp.py
- src/frob/testing/_coverage_refresh.py
- src/frob/testing/_runners.py
- src/frob/tickets/__init__.py
- src/frob/tickets/_evidence.py
- src/frob/tickets/_land.py
- src/frob/tickets/_models.py
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_renumber_v2.py
- src/frob/tickets/_reporting.py
- src/frob/vet/_cache.py
- src/frob/vet/_capability.py
- src/frob/vet/_capability_kotlin.py
- src/frob/vet/_capability_scan.py
- src/frob/vet/_typosquat.py
- tests/integration/test_integration.py
- tests/system/test_cli_scale.py
- tests/test_arch_near_duplicate_native.py
- tests/test_dup_prefilter.py
- tests/test_lang_conformance_gate.py
- tests/unit/strata/test_kernel_properties.py
- tests/unit/strata/test_registry_cross_corpus_totality.py
- tests/unit/strata/test_registry_cross_refs.py
- tests/unit/test_extending_guides_complete.py
evidence_scope:
- tests/unit/test_executable.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/__init__.py
  reason: T-2720 holds a live lease on this file; scope it out of T-2732 to avoid
    collision
  actor: logan
  at: '2026-08-20'
body_changes:
- mode: append
  reason: carry the coordinator's misattribution measurement and detection-vs-regression
    analysis onto the surviving ticket before dropping the duplicate T-2731
  actor: logan
  at: '2026-08-20'
  old_length: 25424
  new_length: 27829
evidence:
- tests/unit/test_executable.py::TestRuffExecutable::test_ruff_finds_errors_in_bad_python
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-2723) at commit b35f47220b8df35922128690bf88cfc38e48e0dc found 137 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (137), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 137 identit(ies).

New (rule, file) identit(ies) filed here:

- ARCH001  src/frob/arch/_concurrency.py
- ARCH001  src/frob/arch/_fallibility.py
- ARCH001  src/frob/arch/_kotlin.py
- ARCH001  src/frob/arch/_python.py
- ARCH001  src/frob/arch/_rust.py
- ARCH001  src/frob/arch/_typescript.py
- ARCH001  src/frob/dup/_pipeline/_normalize.py
- ARCH001  src/frob/dup/_template.py
- ARCH001  src/frob/gates/__init__.py
- ARCH001  src/frob/gates/_dead_symbols.py
- ARCH001  src/frob/gates/_docblocks_refs.py
- ARCH001  src/frob/gates/_ffi_boundary.py
- ARCH001  src/frob/gates/_lang_conformance.py
- ARCH001  src/frob/graph/summary.py
- ARCH001  src/frob/refactor/_scan.py
- ARCH001  src/frob/serve/_events.py
- ARCH001  src/frob/strata/_native_staleness.py
- ARCH001  src/frob/tickets/_evidence.py
- ARCH001  src/frob/tickets/_land.py
- ARCH001  src/frob/tickets/_renumber_v2.py
- ARCH001  src/frob/vet/_capability.py
- ARCH001  src/frob/vet/_capability_kotlin.py
- ARCH102  src/frob/gates/_coverage.py
- ARCH102  src/frob/gitio.py
- ARCH102  src/frob/graph/__init__.py
- ARCH102  src/frob/graph/callgraph.py
- ARCH102  src/frob/lang/__init__.py
- ARCH102  src/frob/lang/_common.py
- ARCH102  src/frob/lang/_support.py
- ARCH102  src/frob/perf/_sketch_store.py
- ARCH102  src/frob/render/_elements.py
- ARCH102  src/frob/stats/_sketch.py
- ARCH102  src/frob/strata/_sysdoc.py
- ARCH102  src/frob/tickets/__init__.py
- ARCH102  src/frob/tickets/_evidence.py
- ARCH102  src/frob/tickets/_models.py
- ARCH102  src/frob/tickets/_reporting.py
- ARCH103  src/frob/app/_check_chunking.py
- ARCH103  src/frob/app/_daemon_proxy.py
- ARCH103  src/frob/app/app.py
- ARCH103  src/frob/app/bind_runner.py
- ARCH103  src/frob/app/cycle_runner.py
- ARCH103  src/frob/app/graph_runner.py
- ARCH103  src/frob/app/parse_runner.py
- ARCH103  src/frob/app/perf_runner.py
- ARCH103  src/frob/app/scaffold_runner.py
- ARCH103  src/frob/app/stats_runner.py
- ARCH103  src/frob/app/ticket_runner/_close_cmd.py
- ARCH103  src/frob/app/ticket_runner/_land_cmd.py
- ARCH103  src/frob/app/ticket_runner/_rapid_sweep.py
- ARCH103  src/frob/check/_ts.py
- ARCH103  src/frob/fuzz/_signatures.py
- ARCH103  src/frob/gates/__init__.py
- ARCH103  src/frob/natives/_build.py
- ARCH103  src/frob/serve/_events.py
- ARCH103  src/frob/serve/_socketd.py
- ARCH103  src/frob/testing/_collect_cpp.py
- ARCH103  src/frob/testing/_coverage_refresh.py
- ARCH103  src/frob/testing/_runners.py
- ARCH103  src/frob/tickets/_new_renumber.py
- ARCH103  src/frob/vet/_cache.py
- E501  /home/logan/projects/frob/src/frob/_cli_parsers/_ticket/_closeout.py
- PERF001  tests/system/test_cli_scale.py
- PERF002  src/frob/arch/_cpp_mayraise.py
- PERF002  src/frob/strata/_sync_may.py
- PERF002  src/frob/vet/_capability.py
- PERF002  src/frob/vet/_capability_scan.py
- PERF002  tests/integration/test_integration.py
- PERF003  scripts/fleet_status.py
- PERF003  src/frob/arch/_fallibility.py
- PERF003  src/frob/arch/_ffi.py
- PERF003  src/frob/arch/_shared_state_race.py
- PERF003  src/frob/cycle/graph.py
- PERF003  src/frob/dup/_pipeline/_normalize.py
- PERF003  src/frob/graph/summary.py
- PERF003  src/frob/perf/_hotpath_smells.py
- PERF003  src/frob/perf/_loop_effects.py
- PERF003  src/frob/perf/_sampler.py
- PERF003  src/frob/strata/_facts.py
- PERF003  src/frob/strata/_models.py
- PERF003  src/frob/vet/_capability_scan.py
- PERF003  src/frob/vet/_typosquat.py
- PERF003  tests/unit/strata/test_kernel_properties.py
- PERF004  scripts/fleet_status.py
- PERF004  src/frob/app/_check_chunking.py
- PERF004  src/frob/app/ticket_runner/_new.py
- PERF004  src/frob/arch/_cpp_mayraise.py
- PERF004  src/frob/arch/_exceptions.py
- PERF004  src/frob/arch/_ocp.py
- PERF004  src/frob/arch/_patterns.py
- PERF004  src/frob/arch/_smells.py
- PERF004  src/frob/arch/_solid.py
- PERF004  src/frob/arch/_typedesign.py
- PERF004  src/frob/deploy/_generate_common.py
- PERF004  src/frob/gates/__init__.py
- PERF004  src/frob/gates/_debt_deprecated.py
- PERF004  src/frob/gates/_deprecated_baseline.py
- PERF004  src/frob/gates/_design_invariants.py
- PERF004  src/frob/gates/_docblocks.py
- PERF004  src/frob/gates/_ffi_boundary.py
- PERF004  src/frob/gates/_lang_conformance.py
- PERF004  src/frob/gates/_registry_exhaustiveness.py
- PERF004  src/frob/gates/_rule_id_scan.py
- PERF004  src/frob/gates/_waive.py
- PERF004  src/frob/gates/_waive_comments.py
- PERF004  src/frob/graph/affects.py
- PERF004  src/frob/graph/summary.py
- PERF004  src/frob/perf/_advisories.py
- PERF004  src/frob/perf/_dup_spawn.py
- PERF004  src/frob/perf/_hotgraph.py
- PERF004  src/frob/refactor/_scan.py
- PERF004  src/frob/strata/_contention.py
- PERF004  src/frob/strata/_design_load.py
- PERF004  src/frob/strata/_distributed_txn.py
- PERF004  src/frob/strata/_elaborate.py
- PERF004  src/frob/strata/_export.py
- PERF004  src/frob/strata/_facts.py
- PERF004  src/frob/strata/_host_isolation.py
- PERF004  src/frob/strata/_infra.py
- PERF004  src/frob/strata/_lint.py
- PERF004  src/frob/strata/_pii.py
- PERF004  src/frob/strata/_selfconform.py
- PERF004  src/frob/strata/_shared_state.py
- PERF004  src/frob/strata/_ssot.py
- PERF004  src/frob/strata/_starvation.py
- PERF004  src/frob/strata/_sync_may.py
- PERF004  src/frob/strata/_threat.py
- PERF004  src/frob/strata/_txn.py
- PERF004  src/frob/tickets/__init__.py
- PERF004  src/frob/tickets/_land.py
- PERF004  tests/test_arch_near_duplicate_native.py
- PERF004  tests/test_dup_prefilter.py
- PERF004  tests/test_lang_conformance_gate.py
- PERF004  tests/unit/strata/test_kernel_properties.py
- PERF004  tests/unit/strata/test_registry_cross_corpus_totality.py
- PERF004  tests/unit/strata/test_registry_cross_refs.py
- PERF004  tests/unit/test_extending_guides_complete.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH001  src/frob/arch/_concurrency.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/arch/_fallibility.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/arch/_kotlin.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/arch/_python.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/arch/_rust.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/arch/_typescript.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/dup/_pipeline/_normalize.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/dup/_template.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/gates/__init__.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/gates/_dead_symbols.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/gates/_docblocks_refs.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/gates/_ffi_boundary.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/gates/_lang_conformance.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/graph/summary.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/refactor/_scan.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/serve/_events.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/strata/_native_staleness.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/tickets/_evidence.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/tickets/_land.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/tickets/_renumber_v2.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/vet/_capability.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/vet/_capability_kotlin.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH102  src/frob/gates/_coverage.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH102  src/frob/gitio.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH102  src/frob/graph/__init__.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH102  src/frob/graph/callgraph.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH102  src/frob/lang/__init__.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH102  src/frob/lang/_common.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH102  src/frob/lang/_support.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH102  src/frob/perf/_sketch_store.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH102  src/frob/render/_elements.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH102  src/frob/stats/_sketch.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH102  src/frob/strata/_sysdoc.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH102  src/frob/tickets/__init__.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH102  src/frob/tickets/_evidence.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH102  src/frob/tickets/_models.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH102  src/frob/tickets/_reporting.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/app/_check_chunking.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/app/_daemon_proxy.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/app/app.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/app/bind_runner.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/app/cycle_runner.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/app/graph_runner.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/app/parse_runner.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/app/perf_runner.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/app/scaffold_runner.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/app/stats_runner.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/app/ticket_runner/_close_cmd.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/app/ticket_runner/_land_cmd.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/app/ticket_runner/_rapid_sweep.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/check/_ts.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/fuzz/_signatures.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/gates/__init__.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/natives/_build.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/serve/_events.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/serve/_socketd.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/testing/_collect_cpp.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/testing/_coverage_refresh.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/testing/_runners.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/tickets/_new_renumber.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/vet/_cache.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/src/frob/_cli_parsers/_ticket/_closeout.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF001  tests/system/test_cli_scale.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF002  src/frob/arch/_cpp_mayraise.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF002  src/frob/strata/_sync_may.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF002  src/frob/vet/_capability.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF002  src/frob/vet/_capability_scan.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF002  tests/integration/test_integration.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF003  scripts/fleet_status.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF003  src/frob/arch/_fallibility.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF003  src/frob/arch/_ffi.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF003  src/frob/arch/_shared_state_race.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF003  src/frob/cycle/graph.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF003  src/frob/dup/_pipeline/_normalize.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF003  src/frob/graph/summary.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF003  src/frob/perf/_hotpath_smells.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF003  src/frob/perf/_loop_effects.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF003  src/frob/perf/_sampler.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF003  src/frob/strata/_facts.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF003  src/frob/strata/_models.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF003  src/frob/vet/_capability_scan.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF003  src/frob/vet/_typosquat.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF003  tests/unit/strata/test_kernel_properties.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  scripts/fleet_status.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/app/_check_chunking.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/app/ticket_runner/_new.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/arch/_cpp_mayraise.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/arch/_exceptions.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/arch/_ocp.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/arch/_patterns.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/arch/_smells.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/arch/_solid.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/arch/_typedesign.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/deploy/_generate_common.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/gates/__init__.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/gates/_debt_deprecated.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/gates/_deprecated_baseline.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/gates/_design_invariants.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/gates/_docblocks.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/gates/_ffi_boundary.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/gates/_lang_conformance.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/gates/_registry_exhaustiveness.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/gates/_rule_id_scan.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/gates/_waive.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/gates/_waive_comments.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/graph/affects.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/graph/summary.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/perf/_advisories.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/perf/_dup_spawn.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/perf/_hotgraph.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/refactor/_scan.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/strata/_contention.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/strata/_design_load.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/strata/_distributed_txn.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/strata/_elaborate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/strata/_export.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/strata/_facts.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/strata/_host_isolation.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/strata/_infra.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/strata/_lint.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/strata/_pii.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/strata/_selfconform.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/strata/_shared_state.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/strata/_ssot.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/strata/_starvation.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/strata/_sync_may.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/strata/_threat.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/strata/_txn.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/tickets/__init__.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/tickets/_land.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  tests/test_arch_near_duplicate_native.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  tests/test_dup_prefilter.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  tests/test_lang_conformance_gate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  tests/unit/strata/test_kernel_properties.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  tests/unit/strata/test_registry_cross_corpus_totality.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  tests/unit/strata/test_registry_cross_refs.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  tests/unit/test_extending_guides_complete.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.



## COORDINATOR ANALYSIS (2026-08-20): these are real, and the blame is wrong

Measured before this ticket was auto-filed:

    b35f47220 (T-2723's land) touched exactly ONE source file:
      src/frob/gates/_gate_cache.py

    quarantined findings span 116 files
    files touched by the blamed land:  0

Every one of the 137 findings also carries `commit_sha: null` and
`ticket_id: null` -- the attribution engine could not connect any of them
to a commit, which is CORRECT, because they predate the batch.

Breakdown:

    PERF004  54     ARCH103  24     ARCH001  22
    ARCH102  15     PERF003  15     PERF002   5
    E501      1     PERF001   1

## Why they all surfaced at once -- this is a DETECTION event, not a regression

Before T-2713 and T-2715 landed, the deferred verification ran under a
budget that silently dropped most gate families and recorded a rolling
baseline of TWO findings against a tree that genuinely had ~40 error
identities -- then reported GREEN and advanced the watermark anyway.

With both repaired, the first COMPLETE verification saw the real floor for
the first time and raised all of it. The machinery is working. But it means
the first honest run after repairing a measurement will always look like a
catastrophic regression, and quarantine currently cannot tell 'newly
detected' from 'newly introduced'.

That distinction is worth building: a finding whose file was untouched by
the blamed batch, carrying a null commit_sha, is a detection event. Consider
whether quarantine should raise on those at all, or raise separately without
blocking deferred landing repo-wide.

## Disposition

Work these as ordinary debt, grouped by rule. PERF004 and ARCH103/ARCH001
dominate and are likely a small number of underlying causes rather than 137
independent problems -- where a group shares one cause, fix the cause and
report the group, as T-1614's waiver audit did (see T-2719, T-2720).

Do NOT dismiss them wholesale. They are real findings that reproduce on
current main.

Per-fix controls, both directions: the finding stops reproducing at the named
site, AND a planted genuine violation of that rule still fires. A narrowing
fix that stops detecting anything is a regression -- this repo has shipped
that mistake before.

Supersedes T-2731, which I filed for this same finding set moments before the
rapid sweep auto-filed this one; T-2731 is dropped as a duplicate.

frob:no-behavior-change reason="136 of 137 quarantined (rule, file)
identities need zero code change -- they are pre-existing debt already
covered by a frob:waive directive (severity note, non-blocking), newly
observed only because the T-2713/T-2715 measurement repair ran a
complete sweep for the first time; nothing about them was introduced by
this ticket's work. The 1 remaining identity (E501 at _closeout.py:23)
is a pure line-wrap of an existing docstring -- same text, same
runtime behavior, only the physical line length changed to satisfy
ruff's 88-char limit. No caller-visible behavior differs before/after
either investigation outcome."