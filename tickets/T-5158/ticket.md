---
id: T-5158
title: 'WAIVE004/010 residue after T-3865: 131 findings (124 lease-free in 84 files,
  17 leased)'
state: queued
kind: bug
origin: human
created: '2026-09-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/**
- tests/**
- strata-core/src/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Residue left by T-3865's first pass at the WAIVE004/WAIVE010 waiver-hygiene
burn-down (T-3844's cluster). T-3865's own pass fixed 219 WAIVE004 and 6
WAIVE010 lease-free findings across 79 files, then stopped at its
~80-file/one-worktree budget with 131 findings still outstanding:
124 WAIVE004 findings across the 84 lease-free files below, plus
17 findings (WAIVE004 and WAIVE010) across 13 files that sat under
another ticket's live lease at scan time and were left untouched --
`frob ticket contention` must be re-run fresh (leases churn fast in this
fleet) before picking any of those back up.

Method (unchanged from T-3865): WAIVE004 sites (a `frob:waive` matching 0
live findings at that site in a full check run) get the comment block
deleted outright, not reworded -- a stale exemption is dead weight that
hides a real regression if the rule ever fires there again. WAIVE010
sites (a `frob:waive` reason reading as deferred/temporary work) get
individually inspected: reword to state the same justification without
the "until"/"pending"/"for now"/"temporarily"/promise-phrase wording if
it is genuinely permanent (confirm directly against
`frob.gates._waive._reason_reads_as_deferred_work`/
`_WAIVE009_PROMISE_PHRASE_RES`), or convert to `frob:debt`/`until=` if it
really is deferred work.

Goal: drive the live WAIVE004/WAIVE010 finding count to zero so T-3844's
own follow-up (promoting WAIVE004/WAIVE010 from warn to error in
frob.toml's [gates.severity] T-1002 managed zone) can proceed safely.

NOTE: this is T-3865's residue_free.txt snapshot at scan time (a handful
of paths may have shifted under concurrent dev churn -- re-derive the
authoritative live list with a fresh full-repo WAIVE004/WAIVE010 check
rather than trusting this text verbatim).

--- Lease-free residue (84 files, 124 WAIVE004 findings) ---
src/frob/gates/_todo_fmt.py
src/frob/gates/_walk_lint.py
src/frob/gitio.py
src/frob/natives/_build.py
src/frob/process/_reap.py
src/frob/process/parsers/ty.py
src/frob/refactor/_scan_carry.py
src/frob/release/_cli.py
src/frob/repo_meta.py
src/frob/serve/_socketd.py
src/frob/strata/_host_isolation_movement.py
src/frob/strata/_selfconform_kinds.py
src/frob/strata/_shrink.py
src/frob/testing/_collect.py
src/frob/testing/_runners.py
src/frob/tickets/_force_override.py
src/frob/tickets/_live_tracker.py
src/frob/vet/_capability_c.py
src/frob/xref/__init__.py
strata-core/src/graph/vmodel/mod.rs
tests/system/test_cli_doctor.py
tests/system/test_fleet_status_ground_truth.py
tests/test_refs_gate.py
tests/test_tickets_organization.py
tests/test_todo_fmt_gate.py
tests/ticket_land_suite/test_claim_close.py
tests/ticket_land_suite/test_wip.py
tests/unit/gates/test_markdown_scan.py
tests/unit/strata/litmus/contention_acl_readonly_vuln.strata
tests/unit/strata/litmus/contention_path_arbitered.strata
tests/unit/strata/litmus/contention_path_clean.strata
tests/unit/strata/litmus/contention_path_vuln.strata
tests/unit/strata/litmus/contention_pipe_clean.strata
tests/unit/strata/litmus/contention_pipe_vuln.strata
tests/unit/strata/litmus/contention_port_clean.strata
tests/unit/strata/litmus/contention_port_vuln.strata
tests/unit/strata/litmus/contention_port_waived.strata
tests/unit/strata/litmus/contention_store_arbitered.strata
tests/unit/strata/litmus/contention_store_clean.strata
tests/unit/strata/litmus/contention_store_vuln.strata
tests/unit/strata/litmus/cwe_352_unfired.strata
tests/unit/strata/litmus/cwe_502_hardened.strata
tests/unit/strata/litmus/cwe_502_vuln.strata
tests/unit/strata/litmus/cwe_798_unfired.strata
tests/unit/strata/litmus/cwe_79_hardened.strata
tests/unit/strata/litmus/cwe_79_vuln.strata
tests/unit/strata/litmus/cwe_89_hardened.strata
tests/unit/strata/litmus/cwe_89_vuln.strata
tests/unit/strata/litmus/cwe_918_hardened.strata
tests/unit/strata/litmus/cwe_918_vuln.strata
tests/unit/strata/litmus/cwe_922_hardened.strata
tests/unit/strata/litmus/cwe_922_vuln.strata
tests/unit/strata/litmus/cwe_exec_hardened.strata
tests/unit/strata/litmus/cwe_exec_vuln.strata
tests/unit/strata/litmus/host_declared.strata
tests/unit/strata/litmus/host_isolation_hardened.strata
tests/unit/strata/litmus/host_isolation_vuln.strata
tests/unit/strata/litmus/host_undeclared.strata
tests/unit/strata/litmus/host_windows_declared.strata
tests/unit/strata/litmus/krb_declared.strata
tests/unit/strata/litmus/krb_movement_hardened.strata
tests/unit/strata/litmus/krb_movement_vuln.strata
tests/unit/strata/litmus/krb_undeclared.strata
tests/unit/strata/litmus/library_exec_foreign_reaches_still_fires.strata
tests/unit/strata/litmus/library_exec_no_foreign_discharges.strata
tests/unit/strata/litmus/lint_hardened.strata
tests/unit/strata/litmus/managed_hardened.strata
tests/unit/strata/litmus/managed_vuln.strata
tests/unit/strata/litmus/pii_hardened.strata
tests/unit/strata/litmus/reliability_health_clean.strata
tests/unit/strata/litmus/reliability_health_missing_vuln.strata
tests/unit/strata/litmus/reliability_health_waived.strata
tests/unit/strata/litmus/reliability_timeout_clean.strata
tests/unit/strata/litmus/reliability_timeout_missing_vuln.strata
tests/unit/strata/litmus/reliability_timeout_waived.strata
tests/unit/strata/litmus/utility_hub_hardened.strata
tests/unit/strata/test_obligation_proof.py
tests/unit/test_app_runners_batch7.py
tests/unit/test_app_runners_json_guard_t2492.py
tests/unit/test_check.py
tests/unit/test_check_admission.py
tests/unit/test_daemon_proxy_lease_t1276.py
tests/unit/test_process_reap.py

--- Leased residue (13 files, 17 findings; re-check leases before touching) ---
Leases observed at T-3865 scan time (re-run `frob ticket contention`
fresh -- these may have already closed): T-4731, T-3032, T-4658, T-3899,
T-5124, T-3995, T-3962, T-5126, T-4760, T-5125, T-4420, plus two
T-draft-* worktrees. One concrete example still true as of T-3865's
final commit: src/frob/tickets/_worktree_sweep.py:91 (WAIVE010) was
claimed mid-pass by T-5123; src/frob/app/ticket_runner/_land_cmd.py:1
(WAIVE010) was leased throughout.
