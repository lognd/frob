---
id: T-2873
title: Write 36 individual COV007 waivers (all but the T-2849-blocked _reap.py finding)
state: done
kind: bug
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/graph_runner.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_ledger_mirror.py
- src/frob/app/ticket_runner/_lifecycle.py
- src/frob/app/ticket_runner/_mutate.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_query.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/app/verify_runner.py
- src/frob/gates/_arch_schema.py
- src/frob/gates/_milestone.py
- src/frob/lang/_support.py
- src/frob/testing/_coverage_refresh.py
- src/frob/tickets/__init__.py
- src/frob/tickets/_archive.py
- src/frob/tickets/_leases.py
- src/frob/tickets/_scope.py
- src/frob/tickets/_store_migrate.py
- src/frob/verify/_backpressure.py
- src/frob/verify/_quarantine.py
- src/frob/verify/_selection.py
- src/frob/verify/_worker.py
- src/frob/vet/_capability_python.py
evidence_scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: add no-behavior-change directive for comment-only waiver batch
  actor: logan
  at: '2026-08-22'
  old_length: 3981
  new_length: 4272
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov007_flags_doc_anchor_on_private_helper
- tests/test_gates.py::TestCoverageGate::test_cov007_silent_for_doc_anchor_on_public_symbol
- tests/test_gates.py::TestCoverageGate::test_cov007_silent_for_a_strata_node_whose_clearance_is_not_public
- tests/test_gates.py::TestCoverageGate::test_cov007_still_fires_for_a_python_private_helper_after_t2549
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 1782e07514af0128b6f7e699ebce7ce436b85fad
---
Split off T-2866: writes the 36 of 37 individually-reasoned frob:waive
COV007 comments that are within reach today (the 37th,
src/frob/process/_reap.py::_FROB_TOKEN_RE, is under T-2849's live
in-progress lease and is tracked separately).

Per-symbol shape, following T-2866's characterization exactly:

Individually-named frob:describes anchor (13, confirmed by grep against
the target doc's frob:describes block with the symbol's own qualified
path):
  src/frob/app/graph_runner.py::_run_select_batch_tests
  src/frob/app/ticket_runner/_new.py::_emit_scope_closure_warnings
  src/frob/app/ticket_runner/_query.py::_stale_lease_reasons
  src/frob/app/ticket_runner/_rapid_sweep.py::_attribute_new_findings
  src/frob/app/ticket_runner/_rapid_sweep.py::_ticket_is_open
  src/frob/app/ticket_runner/_rapid_sweep.py::_warm_tree_clears_unattributed_native_noise
  src/frob/app/ticket_runner/_rapid_sweep.py::_raise_quarantine_for_red_batch
  src/frob/tickets/_scope.py::_scope_add_live_lease_conflict
  src/frob/tickets/_store_migrate.py::_split_done_report
  src/frob/tickets/_store_migrate.py::_migrate_one_v2
  src/frob/verify/_worker.py::_worker_backpressure_reason
  src/frob/verify/_worker.py::_ensure_reduced_priority
  src/frob/vet/_capability_python.py::_python_local_wrapper_capabilities

Many-symbols-one-section convention (23, matching the vet.md shape T-2810
explicitly declined to touch -- several symbols, public and private
alike, citing one feature-level anchor):
  src/frob/app/ticket_runner/_close_cmd.py::_apply_no_behavior_change_directive
  src/frob/app/ticket_runner/_ledger_mirror.py::_UNMIRRORED_TICKET_FILENAMES
  src/frob/app/ticket_runner/_ledger_mirror.py::_mirror_target
  src/frob/app/ticket_runner/_ledger_mirror.py::_commit_mirrored_paths
  src/frob/app/ticket_runner/_lifecycle.py::_refuse_over_broad_scope_on_start
  src/frob/app/ticket_runner/_lifecycle.py::_refuse_empty_scope_on_start
  src/frob/app/ticket_runner/_lifecycle.py::_warn_scope_breadth_on_start
  src/frob/app/ticket_runner/_lifecycle.py::_unblock
  src/frob/app/ticket_runner/_mutate.py::_body
  src/frob/app/ticket_runner/_rapid_sweep.py::_partition_findings_by_attribution
  src/frob/app/ticket_runner/_rapid_sweep.py::_filter_pairs_for_quarantine_raise
  src/frob/app/ticket_runner/_rapid_sweep.py::_dispose_to_existing_duplicate_or_none
  src/frob/app/verify_runner.py::_run_drain_async
  src/frob/gates/_arch_schema.py::_ARCH_DEFAULT_KEYS
  src/frob/gates/_milestone.py::_mile004_unordered_runs_last
  src/frob/lang/_support.py::_unreasoned_names
  src/frob/testing/_coverage_refresh.py::_write_coverage_subprocess_rc
  src/frob/tickets/__init__.py::_doable_sort_key
  src/frob/tickets/_archive.py::_refuse_archive_if_other_worktrees_live
  src/frob/tickets/_leases.py::_scan_for_live_land_process
  src/frob/verify/_backpressure.py::_rapid_soft_warn_thresholds
  src/frob/verify/_quarantine.py::_refuse_if_undisposed
  src/frob/verify/_selection.py::_synthetic_diff_for_touched_symbols

Each waiver's reason text names its own file's actual anchor/section
title -- no templated text reused verbatim across sites (T-1614).

Re-measured after writing (unbudgeted `frob check --only coverage
--json`, worktree t-2866): COV007 note-tier count went from 163 to 199,
exactly +36 (no silent DSL drop, T-2857 hazard checked); COV007
warning-tier count went from 37 to 1 (the _reap.py finding tracked in
T-2874/its landed id). No trailing space before any `\`
continuation, no embedded quote in any `reason=` value -- each verified
by direct read after writing.

No promotion in this ticket: COV007 is not yet at true zero (1 finding
remains, tracked separately). Promotion happens in the follow-up ticket
once that last finding is waived and a full unbudgeted re-measurement
confirms zero.

Acceptance: 36 of COV007's 37 live warnings resolved via individual
frob:waive comments, each citing its own file's actual doc anchor/section
-- verified by the re-measurement above.


frob:no-behavior-change reason="this ticket only adds frob:waive COV007 comments to 23 production files -- no test logic, assertion, or runtime behavior changed; the bound evidence tests exercise the _cov007 gate function itself and are expected to PASS identically at main and at the fix"