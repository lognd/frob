## Done report

Changed:
- design/frob.strata (removed 4 false capability declarations)
- docs/design/registry/capability-via-ratchet.lock.json (removed the now-orphaned vet::fs.write ratchet entry)
- tests/system/test_frob_self_model.py (new narrow regression test)

Investigation (per-node, not batch-resolved -- coordinator's explicit ask):
- checker (bare `may "fs.write";`, no via-list): measured zero fs.write-family
  capability across all of src/frob/check/** via scan_file_capabilities, and
  zero write/dump/remove/rename/mkdir call sites via direct grep. FALSE.
- fleet (bare `may "fs.write";`): same measurement, zero across src/frob/fleet/**. FALSE.
- deploy (bare `may "fs.write";`): same measurement, zero across src/frob/deploy/**
  (subprocess.run calls to cargo/vboxmanage are exec-family, not writes this
  code performs itself). FALSE.
- vet (`may "fs.write" via "_nvd.py", "_registry.py"`): both named files
  measured zero fs.write-family capability AND zero .open()/.write() calls
  of any kind at all -- not even the read-mode-open false-positive shape
  T-2457 fixed, just an ungrounded declaration. FALSE.

All four confirmed FALSE (not genuine capabilities needing declaration) by
direct measurement of the actual code, not assumed from the SYS101 finding
alone. No node in scope had a genuine undeclared write needing the OPPOSITE
fix (declare-not-remove).

Orphaned ratchet cleanup: vet::fs.write's ratchet ceiling (accepted_count=2)
existed only to bound the now-removed via-list; left in place it would be a
ceiling for a capability that no longer exists, the same "permanently
inflated ceiling" shape flagged on the gates::fs.write ratchet in T-2460 --
removed rather than left to rot.

Evidence: 3 pytest node ids in tests/system/test_frob_self_model.py --
test_fragments_module_fs_read_is_declared_not_selfaudit001 and
test_parses_and_elaborates (both still pass, confirming no collateral
damage), plus a new narrow regression test,
test_checker_fleet_deploy_vet_have_no_undeclared_fs_write_selfaudit001,
designated as this ticket's repro (--designate-repro-force). The automated
--check-repro/--designate-repro validation itself could not produce a
verdict (NO_VERDICT: this test loads and elaborates the full strata design
plus the whole SYS gate, exceeding the tool's fixed 60s
_BUG_REPRO_TIMEOUT_S subprocess budget -- a timeout artifact of the check
tool, not evidence against reproduction) -- so the fail-at-parent/pass-at-
fix shape was verified MANUALLY instead: committed the test alone first
(6e181bec1), confirmed it FAILED with 5 unexpected SYS violations against
the still-unfixed design/frob.strata (git checkout -- design/frob.strata
docs/design/registry/capability-via-ratchet.lock.json against that same
tree, observed AssertionError directly), then restored the fix and
confirmed it passes. Full manual transcript is in this ticket's
--designate-repro-reason.

Filed: none

Gates: `frob check --only sys` -- the four SYS101 findings
(node=checker/fleet/deploy/vet, capability='fs.write') are gone; zero new
SYS100 (undeclared-but-observed) findings introduced for any of the four
nodes. Confirmed via a fresh unscoped run after the fix, not a --ticket-
scoped one (SYS/SELFAUDIT is repo-wide regardless of --ticket per section
6c of the playbook).

### Changed
```
 design/frob.strata                                 |  4 ---
 .../registry/capability-via-ratchet.lock.json      |  5 ---
 tests/system/test_frob_self_model.py               | 36 ++++++++++++++++++++++
 tickets/T-2463/ticket.md                           | 19 ++++++++++--
 4 files changed, 53 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_fragments_module_fs_read_is_declared_not_selfaudit001` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_checker_fleet_deploy_vet_have_no_undeclared_fs_write_selfaudit001` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT002@tests/test_gates.py, DUP001@tests/system/test_frob_self_model.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2463/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2463/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2463/src/frob/gates/_dup_graph_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2463/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2463/src/frob/vet/_capability.py, GATERULE001@src/frob/gates/_gates_schema.py, LEXCHECK001@src/frob/vet/_supplychain.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2463, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md, missing-argument@tests/unit/test_ticket_runner_land_release.py
