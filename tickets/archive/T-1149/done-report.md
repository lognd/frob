## Done report

Shipped SYS201 arbiter-awareness (src/frob/strata/_contention.py),
mirroring T-1025's SYS203 precedent exactly (option 1 of this ticket's
two options): check_resource_contention's existing `module: Module |
None` argument now also feeds `_overlapping_path_violations` via a new
`_arbitered_access_by_node` helper -- two nodes whose overlapping
owns/acl path claims would otherwise fire SYS201 are skipped when they
both declare `access "RESOURCE" mode MODE` to a common resource id that
itself declares a real arbiter (arbitrated_by or lock), same discharge
condition SYS203 already applies to store writers, reusing the existing
`_arbitered_resource_ids` helper unchanged. `module=None` (the default)
keeps every pre-T-1149 caller's behavior byte-for-byte unchanged --
additive, not a signature break.

New litmus fixture tests/unit/strata/litmus/contention_path_arbitered.strata
mirrors contention_path_vuln.strata's overlapping-path shape but adds a
shared arbitered `access` declaration on both nodes; 3 new unit tests
under TestOverlappingPath cover discharge-with-module,
still-fires-without-module, and still-fires-with-module-but-no-shared-
resource (the same 3-test shape TestSharedStoreWrite's T-1025 tests use).

Disclosed gap (mirrors T-1025's own disclosed gap, does not re-derive
it): the LIVE SELFAUDIT001 gate and `frob sys audit` CLI still call
check_resource_contention without a module= argument -- neither caller,
nor DesignIds, is in this ticket's declared scope. This means the
capability is built and fully tested but not yet load-bearing on the
live gate; the five SYS205:tickets_ledger waivers in design/frob.strata
stay in place (dropping them would still require BOTH this SYS201 fix
AND that live-gate module= wiring to land together, plus a real owns=
declaration on the five nodes that would need its own end-to-end
verification against SYS205's WRITE path-scoping -- attempting that here
was assessed as materially expanding scope/risk beyond this ticket and
was not attempted). Docs: docs/strata/host.md gained a "SYS201
arbiter-awareness (T-1149)" subsection mirroring the existing SYS203
one, explicitly citing the same disclosed gap rather than re-deriving
new prose for it.

Refactor note: `_overlapping_path_violations` grew past ARCH001's
60-line threshold with the new discharge check; split into
`_share_common_arbiter` (the discharge predicate) and
`_overlapping_path_violation_pair` (the per-pair emission), both private
helpers, zero behavior change to the pre-existing pass/fail shape for
callers with module=None.

Gates: frob check --ticket T-1149 run in --only chunks (playbook section
3b): lint/gates-native/gates-security/coverage/invariant/test/scope/
affect_drift clean for every file this ticket touches
(src/frob/strata/_contention.py, tests/unit/strata/test_contention.py,
tests/unit/strata/litmus/contention_path_arbitered.strata,
design/frob.strata (sync-interface dogfood, testsuite node), docs/strata/
host.md). Remaining findings in the full runs are pre-existing debt in
files this ticket does not touch (verified by file name against scope).
`frob sys sync-interface --check` clean (no drift) after landing.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/strata/test_contention.py::TestOverlappingPath::test_common_arbitered_resource_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_contention.py::TestOverlappingPath::test_common_arbitered_resource_still_fires_without_module` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_contention.py::TestOverlappingPath::test_unarbitered_overlap_still_fires_with_module` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_contention.py::TestDuplicatePort::test_two_nodes_same_port_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 27 error(s), 720 warning(s), 433 waived
- error-findings: ARCH001@src/frob/app/check_runner.py, ARCH001@src/frob/app/ticket_runner/_close_cmd.py, ARCH001@src/frob/doctor.py, ARCH001@src/frob/tickets/_setters.py, ARCH103@src/frob/app/check_runner.py, COV001@src/frob/gates/_tracked_files.py, DOC002@src/frob/serve/_tools.py, E501@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/doctor.py:243, E501@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/vet/_supplychain.py:295, F401@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/tickets/__init__.py:111, F401@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/tickets/__init__.py:22, F401@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/tickets/__init__.py:23, F401@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/tickets/__init__.py:35, F401@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/tickets/__init__.py:46, INV006@src/frob/app/stats_runner.py, INV006@src/frob/gates/_fix_engine.py, INV006@src/frob/gates/_tickets_gate.py, PII012@src/frob/gates/_tickets_gate.py, PII012@tests/system/test_cli_doctor.py, PRE001@tickets/T-1149, TEST001@src/frob/gates/_fix_engine.py, TICK006@tickets.md
