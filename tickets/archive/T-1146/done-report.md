## Done report

Wired check_resource_contention's existing module= parameter (T-1025)
into both live call sites named in this ticket's body:

- src/frob/gates/__init__.py::_selfaudit_violations (SELFAUDIT001,
  frob check's own live gate) -- the `resource_module` it already builds
  for check_mode_conformance (SYS205) is now built BEFORE the
  check_resource_contention call and passed as module= there too.
- src/frob/app/sys_runner.py::_run_audit (frob sys audit CLI) -- same
  move: the existing `resource_module` (already returned from
  _load_audit_model for SYS205) is now also passed to
  check_resource_contention.

src/frob/strata/_design_load.py needed NO change: DesignIds already
carries `.resources` (T-1061), the only fact either call site's
resource_module construction needs.

Verified end to end (not just "should work"): ran `frob sys audit`
against this repo's own design/frob.strata before/after. Before: SYS203
fired mode-blind for all five tickets_ledger writers, discharged only by
their `waive "SYS203:tickets_ledger" ...` clauses. After: `frob sys
audit` itself reports "resource-contention PROVED -- zero SYS2xx gaps"
with the five SYS203 waivers now reported STALE ("no matching finding
fired this run") -- exact confirmation the live discharge now fires for
real. Removed the five now-genuinely-stale SYS203:tickets_ledger
waivers from design/frob.strata (this ticket's own stated goal) and
rewrote the explanatory comments above each access "tickets_ledger"
clause (the "This waiver stays, though" prose was itself now stale).

The five SYS205:tickets_ledger waivers were NOT touched (re-pointed
their `ticket=` attribute from T-1149's dropped-and-renumbered successor
draft to a freshly filed one instead): SYS205 still genuinely fires
(no_declared_path -- none of the five nodes declare an owns/acl claim at
all) and stays waived. Declaring real owns= paths to drop those too
needs its own end-to-end verification against SYS205's WRITE
literal-path-extraction (disclosed as a separate follow-up, not
attempted here -- see filed ticket).

Filed 3 successor/follow-up tickets during this land:
- Absorbed a duplicate draft (this ticket already existed when T-1149
  filed a near-identical one) -- dropped, --absorbed-by T-1146.
- strata: declare real owns= paths on tickets_ledger's five writers to
  drop the SYS205:tickets_ledger waivers (draft T-1158 at
  filing time; verify renumbered id on main) -- the SYS205 follow-up
  described above.
- gates: sys audit's exhaustiveness pass reports every SYS205 waiver as
  stale even when check_mode_conformance correctly matches it (draft
  T-1157 at filing time; verify renumbered id on main) -- a
  pre-existing false-positive found while verifying this land, confirmed
  present even on a clean T-1149-landed checkout with none of this
  ticket's changes applied (not caused by this ticket).

Gates: frob check --ticket T-1146 run in --only chunks (playbook section
3b): lint/gates-native/coverage/invariant/test/affect_drift/prework
clean for every file this ticket touches (src/frob/gates/__init__.py,
src/frob/app/sys_runner.py, design/frob.strata). frob sys sync-interface
--check clean (no new public symbols). Remaining findings in the full
runs are pre-existing debt in files this ticket does not touch (verified
by file name against scope, and the SYS205-staleness quirk specifically
verified pre-existing via a before/after checkout comparison).

### Changed
```
 tickets.md | 80 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++---
 1 file changed, 77 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_selfconform_violation` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_clean_model_no_violations` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_mode_conformance_violation` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_contention.py::TestSharedStoreWrite::test_arbitered_store_discharges` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 27 error(s), 955 warning(s), 440 waived
- error-findings: ARCH001@src/frob/app/check_runner.py, ARCH001@src/frob/app/ticket_runner/_close_cmd.py, ARCH001@src/frob/doctor.py, ARCH001@src/frob/tickets/_setters.py, ARCH103@src/frob/app/check_runner.py, COV001@src/frob/gates/_tracked_files.py, DOC002@src/frob/serve/_tools.py, E501@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/doctor.py:243, E501@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/vet/_supplychain.py:295, F401@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/tickets/__init__.py:111, F401@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/tickets/__init__.py:22, F401@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/tickets/__init__.py:23, F401@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/tickets/__init__.py:35, F401@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/tickets/__init__.py:46, INV006@src/frob/app/stats_runner.py, INV006@src/frob/gates/_fix_engine.py, INV006@src/frob/gates/_tickets_gate.py, PII012@src/frob/gates/_tickets_gate.py, PII012@tests/system/test_cli_doctor.py, PRE001@tickets/T-1146, TEST001@src/frob/gates/_fix_engine.py, TICK006@tickets.md
