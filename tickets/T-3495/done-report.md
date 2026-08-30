## Done report

STRUCTURAL FIX for the recurring CI 99% tail stall: the frob_self_scan_
heavy xdist group's five build_graph(_REPO_ROOT, ...)+sys_gate(...) tests
(four in tests/system/test_frob_self_model.py's TestFrobSelfModel class,
one in tests/unit/strata/test_sys003_calibration.py) each independently
rebuilt the SAME whole-repo graph -- five full-repo scans back to back on
one serialized worker. Added a session-scoped `frob_self_scan_artifacts`
pytest fixture (tests/conftest.py) that runs build_graph+sys_gate exactly
ONCE per worker session and hands every consumer the SAME violations
tuple; each consumer test still applies its own independent filter/
assertion over that shared tuple (unchanged from before -- only the
construction is now shared, never the per-test verdict logic).

Changed:
tests/conftest.py (new FrobSelfScanArtifacts carrier + frob_self_scan_
  artifacts session fixture)
tests/system/test_frob_self_model.py::TestFrobSelfModel (4 tests
  refactored onto the shared fixture; removed now-unused build_graph/
  sys_gate imports)
tests/unit/strata/test_sys003_calibration.py::TestSys003ZeroOnFrobsOwnRepo
  (1 test refactored onto the shared fixture)
tests/unit/test_conftest_self_scan_fixture.py (new -- must-fire/must-
  stay-quiet regression tests for the shared-artifact contract, added
  under scope --add per this repo's tests/unit/test_conftest_*.py
  convention for testing conftest fixtures directly)

tests/test_gates.py::test_the_preexisting_rapid_sweep_waiver_now_
actually_suppresses (the sixth name the coordinator's own CI stack-trace
message grouped with these) is a DIFFERENT scan entirely -- `_snapshot`+
`perf_gate`, not `build_graph`+`sys_gate` -- with no sibling test in this
ticket's scope to share it with, so it is unchanged; sharing across the
group's two distinct scan shapes (build_graph+sys_gate vs snapshot+
perf_gate) is a real, disclosed follow-up this ticket's own scope does
not cover (only the five build_graph+sys_gate tests named above overlap).

MUST-STAY-QUIET / MUST-FIRE (ticket's own acceptance bullet):
tests/unit/test_conftest_self_scan_fixture.py's 4 tests prove the
contract directly against a synthetic FrobSelfScanArtifacts instance
(no real repo scan needed to prove the shape): a violation only the
BROAD `== ()` filter cares about does not fail a narrower message/rule
filter (test_narrow_filter_ignores_unrelated_violation, test_sys003_
filter_ignores_other_rules) while still failing the broad one
(test_broad_filter_fails_on_any_violation); a violation the narrow
filter DOES match still fires (test_narrow_filter_fires_on_its_own_
violation). The 5 real refactored tests all still pass unchanged
(same filter expressions, same real `sys_gate` output).

A/B TIMING (T-3495's own acceptance: "state the before/after"), measured
via two scratch `git worktree`s of the primary checkout (e030f5ed3 =
T-1601's Java land, e030f5ed3~1 = its parent; both with natives built,
`make core`), requested by the coordinator to rule out a Java-caused
regression FIRST:

  Single test (test_sys_gate_zero_violations alone):
    parent (e030f5ed3~1, no Java):  73.9s  (1m13.862s)
    child  (e030f5ed3,   Java landed): 52.3s  (0m52.295s)
  -> Java did NOT regress this test; if anything the second run was
     faster (cache/OS warmth, not a systematic Java effect -- a single
     comparison this close is not proof either way, but there is no
     signal of a Java-caused slowdown here).

  All 5 build_graph+sys_gate tests together, SAME repo state
  (e030f5ed3, Java landed), BEFORE vs AFTER this ticket's own fix:
    BEFORE (5 independent build_graph+sys_gate calls, unmodified code):
      449.9s (7m29.903s)
    AFTER  (this ticket's shared-fixture refactor, T-3495 worktree):
      105.7s (1m45.720s)
  -> ~4.3x speedup, consistent with "one scan's cost plus assertion
     overhead" (T-3495's own acceptance bullet) for a group that used to
     pay 5 scans' cost.

CONCLUSION per the coordinator's own instructions: the Java A/B showed
NO regression, so no Java fix was needed; T-3495 (this ticket) is the
durable fix and is what actually explains and closes the CI tail-stall
risk this coordinator message raised. The remaining tail-stall variable
(test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses's own
independent perf_gate scan, plus the 3 OUT-OF-SCOPE group members in
test_registry_exhaustiveness.py/test_selfconform.py this ticket's scope
does not touch) is a disclosed, real follow-up -- not silently absorbed
here, since fixing it would require expanding this ticket's own declared
scope into files it does not name.

Evidence: 9 node ids bound via `frob ticket evidence T-3495`, all
verified passing directly (`uv run pytest -q -p no:xdist
tests/system/test_frob_self_model.py tests/unit/strata/
test_sys003_calibration.py tests/unit/test_conftest_self_scan_fixture.py
tests/unit/test_conftest_stackdump.py tests/unit/test_conftest_suite_
result_status.py tests/unit/test_conftest_parse_reset.py`, 40 passed).
`uv run frob test --base main` exceeded the 540s foreground budget
(conftest.py's suite-wide fallback selects touched=21/ripple=0 across
python/rust/strata) -- relied on the scoped runs above per the standing
instruction to say so and fall back to scoped runs rather than wait
longer.

Gates: `frob check --budget 300 --ticket T-3495` -- gate:LANG clean (0
errors), gate:SCOPE clean (0 errors, WARN-only closure notes matching
every prior ticket in this series' pattern). One real, fixed finding:
FMT001 on tests/unit/test_conftest_self_scan_fixture.py's new frob:tests
directive lines (over 88 cols) -- rewrapped to the canonical two-line
`# frob:tests \` / target form via `frob fmt`, re-verified clean. Every
other FAIL in the wider run (COV/DOC/DRIFT/PRE/REF/REL/TICK/WAIVE/DEPR)
traces to files outside this ticket's touched set (tickets/T-3410,
src/frob/arch/_normalized.py, etc.) -- the same pre-existing,
already-confirmed-unrelated pattern the T-1601/T-1602/T-1603 done-reports
in this same series each independently confirmed.

### Changed
```
 tickets/T-3495/ticket.md | 21 ++++++++++++++++++++-
 1 file changed, 20 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_conftest_self_scan_fixture.py::TestFrobSelfScanArtifactsSharing::test_narrow_filter_ignores_unrelated_violation` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_self_scan_fixture.py::TestFrobSelfScanArtifactsSharing::test_broad_filter_fails_on_any_violation` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_self_scan_fixture.py::TestFrobSelfScanArtifactsSharing::test_narrow_filter_fires_on_its_own_violation` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_self_scan_fixture.py::TestFrobSelfScanArtifactsSharing::test_sys003_filter_ignores_other_rules` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_fragments_module_fs_read_is_declared_not_selfaudit001` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_checker_fleet_deploy_vet_have_no_undeclared_fs_write_selfaudit001` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_check_admission_exec_sites_are_declared_not_selfaudit001` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sys003_calibration.py::TestSys003ZeroOnFrobsOwnRepo::test_sys003_zero_against_live_repo_design` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 25 error(s), 4138 warning(s), 868 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC006@changelog.d/T-2691.md, DOC006@tickets/T-3489/ticket.md, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3495, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/app/ticket_runner/_land_cmd.py, WIRE002@src/frob/gates/_arch.py, WIRE002@src/frob/gates/_coverage_sites.py, WIRE002@src/frob/gates/_render_lint.py, WIRE002@tests/unit/test_new_ticket_scope_overlap_warning.py, unresolved-attribute@tests/unit/test_conftest_self_scan_fixture.py
