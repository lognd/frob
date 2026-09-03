## Done report

Changed:
tickets T-1382/T-1686 priority (TICK004 rot)
src/frob/app/ticket_runner/_rapid_sweep.py::_file_regression_ticket (DRIFT001 ack)
src/frob/app/ticket_runner/_verify.py::_error_finding_identity (DRIFT001 ack)
src/frob/process/_lock.py::derived_state_lock (DRIFT001 ack)
src/frob/tickets/_land_squash.py::_refuse_if_selfaudit_findings_in_touched_files (DRIFT001 ack)
src/frob/verify/_bisect.py::BisectError / BisectOutcome (DOC007/DRIFT002 :: -> . fix)
src/frob/app/check_runner.py::_claude_config_drift_result (DRIFT002/COV003 stale
  directive fix after T-3600's test rename; also fixes T-3603)
src/frob/tickets/_land_squash.py::classify_test_then_impl_paths and sibling
  (DOC002 anchor fix)
docs/index.md (DOC001: link ledger-mirror-batching.md; REF002: second inbound
  reference to macos-portability.md)
docs/guides/release.md (REF002 second inbound reference)
src/frob/tickets/_land_queue.py::file_lock (COV001 frob:doc)
src/frob/_cli_parsers/_ticket/_metadata.py (OPAQUE001 x2 waiver, standard
  argparse.Action getattr/setattr shape)
tests/test_ticket_leases.py::TestCommitTicketLedgerChange (PII012 x3 waiver,
  git-config-key-name false positive; COV002 class-level frob:ticket)
archived tickets T-1809/T-1969 evidence re-pointed (COV003, orphaned by
  T-3600's test rename)
T-3603 failed as already-resolved by this same fix

Evidence:
tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_identity_less_environment_falls_back_to_throwaway_git_identity
tests/unit/verify/test_bisect.py::TestBisectUnattributedFinding::test_empty_candidates_refuses
tests/unit/verify/test_bisect.py::TestBisectUnattributedFinding::test_converges_to_the_known_culprit_within_log2_n_steps

Measured against the coordinator's CI-authoritative full-check denominator
(run 33439890956, both POSIX legs, 31 errors: DOC 6, DRIFT 6, ARCH 4, COV 4,
PII 3, LARGE 2, OPAQUE 2, TICK 2, REF 1, REL 1):

CLEARED this session: TICK004 (2/2), DRIFT001+DRIFT002 (7/7, one of which
was T-3600's own self-inflicted rename drift, also T-3603), DOC001+DOC002
(3/3), REF002 (1 new finding this session's own DOC001 fix introduced,
also cleared), COV001 (1/1), COV003 (2 of the check_runner rename;
1 more on T-3410 is pre-existing/unrelated -- NOT fixed, see below), PII012
(3/3), OPAQUE001 (2/2).

NOT reachable this session (documented disposition, not silently
dropped):
- ARCH102 x2 (src/frob/process/_lock.py 12 exports/3 clusters,
  src/frob/tickets/_land_squash.py 38 exports/3 clusters) -- module-split
  refactors with real import-breakage risk across many callers; needs its
  own dedicated ticket with a careful split plan, not a rushed burn-down
  edit.
- ARCH103 x2 (src/frob/tickets/_leases.py::_land_flock_probe,
  ::_live_pids_with_cwd) -- mixed-concern function decomposition;
  moderate refactor risk, needs its own ticket.
- LARGE001 x2 (.claude/hooks/root-write-guard.py 834 lines,
  src/frob/arch/_mayraise.py 878 lines) -- file-split refactors; real
  risk of breaking hook wiring/behavior if rushed.
- REL001 (frob:debt CYCLE001 at src/frob/__init__.py, ticket=T-3411) --
  T-3411 is explicitly titled "Owner decision needed"; not mine to
  resolve unilaterally.
- COV003 on T-3410 (cmd: evidence on a kind=bug ticket, only valid for
  docs/ux) -- pre-existing, unrelated to any of this session's diffs;
  needs its own scoped fix (replace with pytest node ids) rather than a
  guess under this ticket's own time budget.

Filed: none (T-3603 addressed via `frob ticket fail`, not a new filing)

Gates: frob check --ticket T-3590 clean on gate:SCOPE/gate:PRE (sweep
refreshed). BUG002/TEST016 addressed via --skip-mutation-evidence at land
(T-0755): every bound test is a PRE-EXISTING, already-passing regression
lock, not a new behavior change -- this ticket's own fixes are directive/
waiver/doc corrections (stale test-name citations, missing doc anchors,
argparse/PII false-positive waivers, ticket triage), not code behavior
changes a mutation-killing test could target.
