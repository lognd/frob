---
id: T-2866
title: Write 37 individual COV007 waivers across 24 files, then promote to error
state: in-progress
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/process/_reap.py
  reason: T-2849 holds an in-progress lease on this file; narrowing to avoid collision,
    will handle _FROB_TOKEN_RE's COV007 waiver in a follow-up or after T-2849 lands
  actor: logan
  at: '2026-08-22'
- op: remove
  glob: src/frob/gates/__init__.py
  reason: T-2849 holds an in-progress lease; writing the 37 waivers first (none touch
    this file), will re-add for the promotion step once T-2849 lands
  actor: logan
  at: '2026-08-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split off T-2370. COV007 (frob:doc on a private symbol) is NOT collapsible
-- 37 live warnings across 24 files, each an individually-reasoned honest
waive, not a code fix and not a single glob change (REG008 shape, not
REF001 shape).

Full per-symbol characterization, measured 2026-08-22 (worktree t-2370,
frob check --only coverage --json unbudgeted, exit 1, gate-summary
present):

  src/frob/app/graph_runner.py:44 _run_select_batch_tests
  src/frob/app/ticket_runner/_close_cmd.py:1183 _apply_no_behavior_change_directive
  src/frob/app/ticket_runner/_ledger_mirror.py:279 _UNMIRRORED_TICKET_FILENAMES
  src/frob/app/ticket_runner/_ledger_mirror.py:418 _mirror_target
  src/frob/app/ticket_runner/_ledger_mirror.py:430 _commit_mirrored_paths
  src/frob/app/ticket_runner/_lifecycle.py:1067 _refuse_over_broad_scope_on_start
  src/frob/app/ticket_runner/_lifecycle.py:1120 _refuse_empty_scope_on_start
  src/frob/app/ticket_runner/_lifecycle.py:1218 _warn_scope_breadth_on_start
  src/frob/app/ticket_runner/_lifecycle.py:1380 _unblock
  src/frob/app/ticket_runner/_mutate.py:473 _body
  src/frob/app/ticket_runner/_new.py:955 _emit_scope_closure_warnings
  src/frob/app/ticket_runner/_query.py:945 _stale_lease_reasons
  src/frob/app/ticket_runner/_rapid_sweep.py:1126 _attribute_new_findings
  src/frob/app/ticket_runner/_rapid_sweep.py:1175 _ticket_is_open
  src/frob/app/ticket_runner/_rapid_sweep.py:1200 _partition_findings_by_attribution
  src/frob/app/ticket_runner/_rapid_sweep.py:1276 _warm_tree_clears_unattributed_native_noise
  src/frob/app/ticket_runner/_rapid_sweep.py:1323 _filter_pairs_for_quarantine_raise
  src/frob/app/ticket_runner/_rapid_sweep.py:1397 _raise_quarantine_for_red_batch
  src/frob/app/ticket_runner/_rapid_sweep.py:1955 _dispose_to_existing_duplicate_or_none
  src/frob/app/verify_runner.py:324 _run_drain_async
  src/frob/gates/_arch_schema.py:62 _ARCH_DEFAULT_KEYS
  src/frob/gates/_milestone.py:344 _mile004_unordered_runs_last
  src/frob/lang/_support.py:327 _unreasoned_names
  src/frob/process/_reap.py:369 _FROB_TOKEN_RE
  src/frob/testing/_coverage_refresh.py:115 _write_coverage_subprocess_rc
  src/frob/tickets/__init__.py:362 _doable_sort_key
  src/frob/tickets/_archive.py:207 _refuse_archive_if_other_worktrees_live
  src/frob/tickets/_leases.py:1876 _scan_for_live_land_process
  src/frob/tickets/_scope.py:292 _scope_add_live_lease_conflict
  src/frob/tickets/_store_migrate.py:106 _split_done_report
  src/frob/tickets/_store_migrate.py:144 _migrate_one_v2
  src/frob/verify/_backpressure.py:491 _rapid_soft_warn_thresholds
  src/frob/verify/_quarantine.py:449 _refuse_if_undisposed
  src/frob/verify/_selection.py:93 _synthetic_diff_for_touched_symbols
  src/frob/verify/_worker.py:328 _worker_backpressure_reason
  src/frob/verify/_worker.py:377 _ensure_reduced_priority
  src/frob/vet/_capability_python.py:1281 _python_local_wrapper_capabilities

Method used: for each symbol, read its frob:doc anchor, then checked the
anchor's target doc file for a frob:describes directive individually
naming the private symbol by its qualified path.

About a third resolve to an individually-named frob:describes anchor --
unambiguous honest-waive candidates, no further check needed:
_scope_add_live_lease_conflict, _attribute_new_findings, _ticket_is_open,
_warm_tree_clears_unattributed_native_noise, _raise_quarantine_for_red_batch,
_doable_sort_key, _split_done_report, _migrate_one_v2,
_worker_backpressure_reason, _ensure_reduced_priority,
_python_local_wrapper_capabilities (via docs/modules/vet.md's precedent).

The remaining roughly two-thirds do NOT carry an individually-named
frob:describes block but also do NOT match the T-2810 duplicate-anchor bug
shape (T-2810's fix removed a private helper's frob:doc only where a
PUBLIC sibling in the SAME file already carried the IDENTICAL directive as
a genuine, meaningless copy). Here the pattern is consistent across every
file checked: many symbols, public and private alike, in the same file all
cite the SAME section-level anchor (one conceptual feature -- e.g.
"backpressure", "quarantine circuit breaker", "adapter capability
contract"), each comment marking where in the code that piece of the
section's behavior lives. This matches the many-symbols-one-section
convention this repo already accepted for vet.md (T-2810 explicitly
declined to touch it), not a duplicate. Zero of the 37 need a code fix;
zero exhibit the T-2810 bug.

Remaining work: write 37 individually-reasoned frob:waive COV007
comments (one per symbol above, citing its specific doc anchor), grouped
by file cluster, re-measuring after each group per the T-2857 silent-drop
DSL hazard (unescaped quote in reason=, unquoted reason=, trailing space
before a backslash continuation all silently drop a directive with no
error). Then re-run frob check --only coverage --json unbudgeted for a
confirmed true zero before promoting COV007's severity to ERROR in its
gate module (frob/gates/__init__.py::_cov007) -- unlike COV006, COV007's
own docstring does NOT forbid promotion; it is fine once genuinely zero.

Acceptance: (0) zero COV007 warnings via the same command, (1) COV007
promoted from WARN to ERROR in frob/gates/__init__.py.
